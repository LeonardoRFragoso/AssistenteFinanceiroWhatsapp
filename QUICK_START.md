# Guia Rápido de Inicialização

## Problemas Corrigidos ✅

Este guia assume que você já aplicou as correções documentadas em `MIGRATION_FIX.md`.

### Correções Aplicadas:
1. ✅ Migration do `paymentmethod` agora é idempotente
2. ✅ Documentação para SECRET_KEY segura (64+ caracteres)
3. ✅ Scripts utilitários criados

## Passo a Passo para Iniciar

### 1. Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Gerar SECRET_KEY segura
python scripts/generate_secret_key.py

# Editar .env e adicionar a SECRET_KEY gerada
# Também configure outras variáveis necessárias (API keys, etc.)
```

### 2. Validar Configuração

```bash
# Validar ambiente antes de iniciar
python scripts/validate_environment.py
```

### 3. Iniciar Aplicação

```bash
# Iniciar todos os serviços
docker-compose up -d

# Verificar logs
docker-compose logs -f backend
```

### 4. Verificar Saúde dos Serviços

```bash
# PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Redis
docker-compose exec redis redis-cli ping

# Backend (verificar se está respondendo)
curl http://localhost:8000/health

# Ngrok (obter URL pública)
curl http://localhost:4040/api/tunnels
```

## Comandos Úteis

### Gerenciamento de Containers

```bash
# Ver status dos containers
docker-compose ps

# Ver logs de um serviço específico
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f ngrok

# Reiniciar um serviço
docker-compose restart backend

# Parar todos os serviços
docker-compose down

# Parar e remover volumes (CUIDADO: apaga dados!)
docker-compose down -v
```

### Migrations

```bash
# Ver status atual das migrations
docker-compose exec backend alembic current

# Aplicar migrations pendentes
docker-compose exec backend alembic upgrade head

# Reverter última migration
docker-compose exec backend alembic downgrade -1

# Ver histórico de migrations
docker-compose exec backend alembic history
```

### Banco de Dados

```bash
# Acessar PostgreSQL
docker-compose exec postgres psql -U postgres -d financial_assistant

# Verificar tabelas
docker-compose exec postgres psql -U postgres -d financial_assistant -c "\dt"

# Verificar enum paymentmethod
docker-compose exec postgres psql -U postgres -d financial_assistant -c "\dT+ paymentmethod"

# Ver estrutura da tabela transactions
docker-compose exec postgres psql -U postgres -d financial_assistant -c "\d transactions"
```

### Desenvolvimento

```bash
# Reconstruir imagens após mudanças no código
docker-compose up --build

# Acessar shell do backend
docker-compose exec backend bash

# Executar testes (se configurados)
docker-compose exec backend pytest

# Ver variáveis de ambiente do backend
docker-compose exec backend env
```

## Troubleshooting

### Backend não inicia

1. Verificar logs:
   ```bash
   docker-compose logs backend --tail=100
   ```

2. Verificar se PostgreSQL está pronto:
   ```bash
   docker-compose exec postgres pg_isready
   ```

3. Verificar variáveis de ambiente:
   ```bash
   docker-compose exec backend env | grep -E "(DATABASE|SECRET|REDIS)"
   ```

### Erro na Migration

1. Verificar status:
   ```bash
   docker-compose exec backend alembic current
   ```

2. Se necessário, fazer downgrade e upgrade:
   ```bash
   docker-compose exec backend alembic downgrade base
   docker-compose exec backend alembic upgrade head
   ```

### Ngrok não conecta

1. Verificar se backend está rodando:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verificar token do Ngrok no .env:
   ```bash
   grep NGROK_AUTHTOKEN .env
   ```

3. Ver logs do Ngrok:
   ```bash
   docker-compose logs ngrok
   ```

## URLs Importantes

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Ngrok Dashboard**: http://localhost:4040
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Próximos Passos

1. ✅ Configure todas as API keys no `.env`
2. ✅ Teste o webhook do WhatsApp via Ngrok
3. ✅ Configure o Twilio com a URL do Ngrok
4. ✅ Teste envio de mensagens

## Segurança

⚠️ **IMPORTANTE**:
- NUNCA faça commit do arquivo `.env`
- Use SECRET_KEY diferentes para cada ambiente
- Mantenha as API keys seguras
- Em produção, use HTTPS e configure CORS adequadamente

## Suporte

Para mais detalhes sobre as correções aplicadas, consulte:
- `MIGRATION_FIX.md` - Documentação das correções
- `scripts/generate_secret_key.py` - Gerar SECRET_KEY
- `scripts/validate_environment.py` - Validar configuração
