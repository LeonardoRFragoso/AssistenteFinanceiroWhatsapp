# 🔧 CORRIGIR CREDENCIAIS DO TWILIO

## ❌ Problema Identificado

O arquivo `.env` ainda está com valores de exemplo:
- `TWILIO_ACCOUNT_SID=seu_account_sid_aqui`
- `TWILIO_AUTH_TOKEN=seu_auth_token_aqui`

## ✅ Solução

### 1. Abra o arquivo .env

```powershell
notepad .env
```

### 2. Localize e Substitua as Credenciais

Procure estas linhas e substitua pelos valores REAIS da sua conta Twilio:

**ANTES (errado):**
```env
TWILIO_ACCOUNT_SID=seu_account_sid_aqui
TWILIO_AUTH_TOKEN=seu_auth_token_aqui
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

**DEPOIS (correto):**
```env
TWILIO_ACCOUNT_SID=SEU_ACCOUNT_SID_AQUI
TWILIO_AUTH_TOKEN=SEU_AUTH_TOKEN_REAL_AQUI
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### 3. Onde Encontrar Suas Credenciais

**Account SID:** (do console Twilio)
- Acesse: https://console.twilio.com
- Copie o Account SID que começa com "AC"

**Auth Token:** (da sua segunda imagem)
- Está na seção "Auth Token" 
- Clique em "Show" se estiver oculto
- Copie o valor completo

### 4. Salvar e Reiniciar

Depois de editar o `.env`:

```powershell
# Salve o arquivo .env
# Depois reinicie o backend
docker-compose restart backend
```

### 5. Aguardar Backend Iniciar

```powershell
# Aguarde 10 segundos
Start-Sleep -Seconds 10

# Verifique se iniciou
docker-compose logs backend --tail=5
```

### 6. Testar Novamente

```powershell
.\test-whatsapp.ps1
```

## 📋 Checklist

- [ ] Abrir arquivo `.env`
- [ ] Substituir `TWILIO_ACCOUNT_SID` pelo valor do console Twilio
- [ ] Substituir `TWILIO_AUTH_TOKEN` pelo valor real da imagem
- [ ] Salvar arquivo `.env`
- [ ] Executar `docker-compose restart backend`
- [ ] Aguardar 10 segundos
- [ ] Executar `.\test-whatsapp.ps1`

## ⚠️ IMPORTANTE

O Auth Token é sensível! Não compartilhe publicamente.
