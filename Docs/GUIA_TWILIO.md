# 🚀 Guia Rápido - Twilio WhatsApp

## 📝 Passo 1: Configurar Credenciais

Edite o arquivo `.env` na raiz do projeto e adicione suas credenciais do Twilio:

```bash
# Abra o arquivo .env
nano .env
```

Adicione/atualize estas linhas com suas credenciais reais:

```env
TWILIO_ACCOUNT_SID=SEU_ACCOUNT_SID_AQUI
TWILIO_AUTH_TOKEN=seu_auth_token_aqui
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

**⚠️ IMPORTANTE:** Substitua `seu_auth_token_aqui` pelo Auth Token que aparece na sua segunda imagem do console Twilio.

## 📱 Passo 2: Ativar WhatsApp Sandbox

1. Acesse: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
2. Você verá um código como: `join <palavra-código>`
3. Do seu WhatsApp pessoal, envie uma mensagem para `+1 415 523 8886` com o texto:
   ```
   join <palavra-código>
   ```
4. Você receberá uma confirmação no WhatsApp

## 🔄 Passo 3: Reiniciar Backend

```bash
docker-compose restart backend
```

Aguarde alguns segundos para o backend iniciar.

## ✅ Passo 4: Verificar Configuração

Teste se as credenciais estão configuradas:

```bash
curl http://localhost:8000/test/twilio-status
```

Você deve ver:
```json
{
  "configured": true,
  "account_sid_set": true,
  "auth_token_set": true,
  "whatsapp_number_set": true,
  "whatsapp_number": "whatsapp:+14155238886"
}
```

## 📤 Passo 5: Enviar Mensagem de Teste

Envie uma mensagem de teste para o seu WhatsApp:

```bash
curl -X POST http://localhost:8000/test/send-whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+5521999999999",
    "message": "Olá! Esta é uma mensagem de teste do Assistente Financeiro."
  }'
```

**Substitua** `+5521999999999` pelo seu número de WhatsApp (com código do país e DDD).

## 🎯 Passo 6: Configurar Webhook (Receber Mensagens)

Para que o sistema receba mensagens do WhatsApp, você precisa configurar um webhook.

### Opção A: Desenvolvimento Local com ngrok

1. Instale o ngrok: https://ngrok.com/download

2. Execute o ngrok:
```bash
ngrok http 8000
```

3. Copie a URL HTTPS que aparece (ex: `https://abc123.ngrok.io`)

4. No console Twilio, vá em:
   - **Messaging** > **Settings** > **WhatsApp Sandbox Settings**
   - Em "When a message comes in", cole: `https://abc123.ngrok.io/webhook/whatsapp`
   - Método: **POST**
   - Clique em **Save**

### Opção B: Produção

Configure o webhook com sua URL de produção:
```
https://seu-dominio.com/webhook/whatsapp
```

## 💬 Passo 7: Testar Conversação

Do seu WhatsApp, envie mensagens para o número Twilio:

### Registrar Despesa
```
Gastei R$ 50.00 com almoço
```

### Registrar Receita
```
Recebi R$ 3500 de salário
```

### Criar Lembrete
```
Lembrar de pagar conta amanhã
```

### Consultar Saldo
```
Qual meu saldo?
```

## 🔍 Verificar Logs

Para ver se as mensagens estão sendo processadas:

```bash
# Logs do backend
docker-compose logs -f backend

# Filtrar apenas Twilio
docker-compose logs backend | grep -i twilio
```

## 📊 Endpoints Disponíveis

### Verificar Status
```bash
GET http://localhost:8000/test/twilio-status
```

### Enviar Mensagem
```bash
POST http://localhost:8000/test/send-whatsapp
Content-Type: application/json

{
  "to": "+5521999999999",
  "message": "Sua mensagem aqui"
}
```

### Webhook (Receber Mensagens)
```bash
POST http://localhost:8000/webhook/whatsapp
```

## 🐛 Troubleshooting

### Erro: "Unable to create record"
- Verifique se o Auth Token está correto
- Confirme que o Account SID está correto
- Reinicie o backend: `docker-compose restart backend`

### Erro: "Unverified numbers"
- No sandbox, apenas números que enviaram "join" podem receber mensagens
- Certifique-se de ter ativado o sandbox no seu WhatsApp

### Mensagens não chegam
- Verifique se o webhook está configurado corretamente
- Use ngrok para desenvolvimento local
- Verifique os logs: `docker-compose logs -f backend`

### Erro 401 Unauthorized
- O Auth Token está incorreto
- Verifique o arquivo `.env`
- Reinicie o backend após alterar o `.env`

## 📱 Console Twilio

Acesse para monitorar mensagens:
- **Dashboard**: https://console.twilio.com/us1/dashboard
- **Logs de Mensagens**: https://console.twilio.com/us1/monitor/logs/sms
- **WhatsApp Sandbox**: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn

## 🎓 Documentação Oficial

- Twilio WhatsApp: https://www.twilio.com/docs/whatsapp
- API Reference: https://www.twilio.com/docs/sms/api
- Sandbox Guide: https://www.twilio.com/docs/whatsapp/sandbox

## ⚡ Comandos Rápidos

```bash
# Verificar status
curl http://localhost:8000/test/twilio-status

# Enviar teste
curl -X POST http://localhost:8000/test/send-whatsapp \
  -H "Content-Type: application/json" \
  -d '{"to": "+5521999999999", "message": "Teste"}'

# Ver logs
docker-compose logs -f backend | grep -i twilio

# Reiniciar backend
docker-compose restart backend

# Iniciar ngrok
ngrok http 8000
```

## 🎉 Pronto!

Agora você pode:
1. ✅ Enviar mensagens WhatsApp do sistema
2. ✅ Receber mensagens dos usuários
3. ✅ Processar comandos financeiros
4. ✅ Usar IA para responder automaticamente

**Dica:** Mantenha o ngrok rodando durante o desenvolvimento para receber mensagens!
