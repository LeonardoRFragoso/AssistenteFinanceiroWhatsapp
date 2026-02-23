# 🪟 Comandos PowerShell para Twilio

## ✅ Verificar Status do Twilio

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/test/twilio-status" -UseBasicParsing
```

## 📤 Enviar Mensagem WhatsApp

### Opção 1: Usando o Script (RECOMENDADO)

1. Edite o arquivo `test-whatsapp.ps1` e coloque seu número
2. Execute:

```powershell
.\test-whatsapp.ps1
```

### Opção 2: Comando Direto

```powershell
$headers = @{
    "Content-Type" = "application/json"
}

$body = @"
{
    "to": "+5521999999999",
    "message": "Olá! Teste do Assistente Financeiro."
}
"@

Invoke-RestMethod -Uri "http://localhost:8000/test/send-whatsapp" -Method POST -Headers $headers -Body $body
```

### Opção 3: Com Variáveis

```powershell
$numero = "+5521999999999"
$mensagem = "Olá! Esta é uma mensagem de teste."

$body = @"
{
    "to": "$numero",
    "message": "$mensagem"
}
"@

$headers = @{"Content-Type" = "application/json"}

Invoke-RestMethod -Uri "http://localhost:8000/test/send-whatsapp" -Method POST -Headers $headers -Body $body
```

## 📋 Ver Logs do Backend

```powershell
# Ver últimas 20 linhas
docker-compose logs backend --tail=20

# Seguir logs em tempo real
docker-compose logs -f backend

# Filtrar apenas Twilio
docker-compose logs backend | Select-String -Pattern "twilio"
```

## 🔍 Verificar Documentação da API

```powershell
Start-Process "http://localhost:8000/docs"
```

## 🔄 Reiniciar Backend

```powershell
docker-compose restart backend
```

## 📊 Ver Status de Todos os Containers

```powershell
docker-compose ps
```

## 🧪 Testar Endpoint de Health

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -UseBasicParsing
```

## 💡 Dicas

1. **Sempre use `-UseBasicParsing`** para evitar avisos de segurança
2. **Use aspas duplas `"` para strings JSON**, não aspas simples
3. **Para números de telefone**, sempre inclua o código do país (+55 para Brasil)
4. **Formato do número**: `+5521999999999` (sem espaços ou hífens)

## ⚠️ Troubleshooting

### Erro: "There was an error parsing the body"
- Use o script `test-whatsapp.ps1` ao invés de comandos diretos
- Certifique-se de usar aspas duplas no JSON

### Erro: "Unable to create record"
- Verifique se o Auth Token está correto no `.env`
- Reinicie o backend: `docker-compose restart backend`

### Mensagem não chega
- Ative o sandbox primeiro (veja imagem do console Twilio)
- Envie "join <código>" para +1 415 523 8886
- Verifique se o número está no formato correto

## 📱 Ativar WhatsApp Sandbox

Veja a imagem que você compartilhou! Você precisa:

1. Escanear o QR Code com seu WhatsApp
   OU
2. Enviar mensagem para `+1 415 523 8886` com o texto:
   ```
   join <código-que-aparece-na-tela>
   ```

Depois disso, você poderá receber mensagens do sistema!
