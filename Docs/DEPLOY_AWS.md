# 🚀 Deploy AWS - Guia Completo

## Pré-requisitos

- Conta AWS ativa
- AWS CLI instalado e configurado
- Domínio registrado
- Credenciais: Twilio, OpenAI, Mercado Pago

---

## 1. Configurar Infraestrutura AWS

### 1.1 Criar VPC e Subnets

```bash
# Criar VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=financial-assistant-vpc}]'

# Criar Subnets públicas (2 AZs para alta disponibilidade)
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1b
```

### 1.2 Criar RDS PostgreSQL

```bash
aws rds create-db-instance \
    --db-instance-identifier financial-assistant-db \
    --db-instance-class db.t3.small \
    --engine postgres \
    --engine-version 15.4 \
    --master-username postgres \
    --master-user-password SEU_PASSWORD_SEGURO \
    --allocated-storage 20 \
    --storage-type gp3 \
    --vpc-security-group-ids sg-xxx \
    --db-subnet-group-name seu-subnet-group \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --multi-az
```

### 1.3 Criar ElastiCache Redis

```bash
aws elasticache create-cache-cluster \
    --cache-cluster-id financial-assistant-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --cache-subnet-group-name seu-subnet-group \
    --security-group-ids sg-xxx
```

### 1.4 Criar EC2 Instances

```bash
# Criar instância para backend
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type t3.medium \
    --key-name sua-chave \
    --security-group-ids sg-xxx \
    --subnet-id subnet-xxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=financial-assistant-backend}]' \
    --user-data file://user-data.sh
```

---

## 2. Configurar Servidor EC2

### 2.1 Conectar ao Servidor

```bash
ssh -i sua-chave.pem ubuntu@seu-ip-publico
```

### 2.2 Instalar Dependências

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Instalar Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Instalar Git
sudo apt install -y git
```

### 2.3 Clonar Repositório

```bash
cd /opt
sudo git clone https://github.com/seu-usuario/seu-repo.git financial-assistant
cd financial-assistant
sudo chown -R ubuntu:ubuntu /opt/financial-assistant
```

### 2.4 Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env
```

Configurar:
```env
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@seu-rds-endpoint:5432/financial_assistant
REDIS_URL=redis://seu-elasticache-endpoint:6379/0

SECRET_KEY=gere-uma-chave-segura-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

TWILIO_ACCOUNT_SID=seu_twilio_sid
TWILIO_AUTH_TOKEN=seu_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

OPENAI_API_KEY=sua_openai_key
OPENAI_MODEL=gpt-4o

MERCADO_PAGO_ACCESS_TOKEN=seu_mp_token
MERCADO_PAGO_PUBLIC_KEY=sua_mp_public_key

FRONTEND_URL=https://seudominio.com
BACKEND_URL=https://api.seudominio.com

WORKER_ENABLED=true
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## 3. Configurar Banco de Dados

```bash
# Rodar migrações
docker-compose run backend alembic upgrade head

# Seed dos planos
docker-compose run backend python seed_plans.py
```

---

## 4. Configurar Nginx

### 4.1 Backend (API)

```bash
sudo nano /etc/nginx/sites-available/api.seudominio.com
```

```nginx
server {
    listen 80;
    server_name api.seudominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts para webhooks
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 4.2 Frontend

```bash
sudo nano /etc/nginx/sites-available/seudominio.com
```

```nginx
server {
    listen 80;
    server_name seudominio.com www.seudominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4.3 Ativar Sites

```bash
sudo ln -s /etc/nginx/sites-available/api.seudominio.com /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/seudominio.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 5. Configurar SSL (Let's Encrypt)

```bash
sudo certbot --nginx -d seudominio.com -d www.seudominio.com -d api.seudominio.com
```

Certbot irá:
- Gerar certificados SSL
- Configurar HTTPS automaticamente
- Configurar renovação automática

---

## 6. Iniciar Aplicação

```bash
cd /opt/financial-assistant
docker-compose -f docker-compose.prod.yml up -d
```

Verificar logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 7. Configurar Webhooks

### 7.1 Twilio WhatsApp

1. Acesse: https://console.twilio.com/
2. Vá em Messaging > Settings > WhatsApp Sandbox
3. Configure webhook: `https://api.seudominio.com/webhook/whatsapp`
4. Método: POST
5. Salve

### 7.2 Mercado Pago

1. Acesse: https://www.mercadopago.com.br/developers
2. Vá em Suas integrações > Webhooks
3. Configure URL: `https://api.seudominio.com/billing/webhook/mercado-pago`
4. Eventos: `payment`, `subscription_preapproval`
5. Salve

---

## 8. Configurar Monitoramento

### 8.1 CloudWatch Logs

```bash
# Instalar CloudWatch Agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
```

Configurar `/opt/aws/amazon-cloudwatch-agent/etc/config.json`:

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/financial-assistant/backend/logs/*.log",
            "log_group_name": "/aws/ec2/financial-assistant",
            "log_stream_name": "{instance_id}/backend"
          }
        ]
      }
    }
  }
}
```

### 8.2 Alarmes CloudWatch

```bash
# CPU alta
aws cloudwatch put-metric-alarm \
    --alarm-name financial-assistant-high-cpu \
    --alarm-description "CPU acima de 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2
```

---

## 9. Backup e Recuperação

### 9.1 Backup Automático RDS

Já configurado com `--backup-retention-period 7`

### 9.2 Backup Manual

```bash
# Backup do banco
docker-compose exec backend pg_dump -U postgres -h seu-rds-endpoint financial_assistant > backup.sql

# Upload para S3
aws s3 cp backup.sql s3://seu-bucket/backups/backup-$(date +%Y%m%d).sql
```

### 9.3 Script de Backup Automático

```bash
sudo nano /opt/backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T backend pg_dump -U postgres -h seu-rds-endpoint financial_assistant | gzip > /opt/backups/backup_$DATE.sql.gz
aws s3 cp /opt/backups/backup_$DATE.sql.gz s3://seu-bucket/backups/
find /opt/backups/ -name "*.sql.gz" -mtime +7 -delete
```

```bash
chmod +x /opt/backup.sh
crontab -e
# Adicionar: 0 3 * * * /opt/backup.sh
```

---

## 10. Segurança

### 10.1 Security Groups

**Backend SG**:
- Inbound: 8000 (do Load Balancer), 22 (seu IP)
- Outbound: All

**RDS SG**:
- Inbound: 5432 (do Backend SG)
- Outbound: None

**Redis SG**:
- Inbound: 6379 (do Backend SG)
- Outbound: None

### 10.2 IAM Roles

Criar role para EC2 com políticas:
- CloudWatchAgentServerPolicy
- AmazonS3ReadOnlyAccess (para backups)

---

## 11. Escalabilidade

### 11.1 Load Balancer

```bash
# Criar Application Load Balancer
aws elbv2 create-load-balancer \
    --name financial-assistant-alb \
    --subnets subnet-xxx subnet-yyy \
    --security-groups sg-xxx
```

### 11.2 Auto Scaling Group

```bash
# Criar Launch Template
aws ec2 create-launch-template \
    --launch-template-name financial-assistant-template \
    --version-description "v1" \
    --launch-template-data file://launch-template.json

# Criar Auto Scaling Group
aws autoscaling create-auto-scaling-group \
    --auto-scaling-group-name financial-assistant-asg \
    --launch-template LaunchTemplateName=financial-assistant-template \
    --min-size 2 \
    --max-size 10 \
    --desired-capacity 2 \
    --target-group-arns arn:aws:elasticloadbalancing:xxx
```

---

## 12. Manutenção

### 12.1 Atualizar Aplicação

```bash
cd /opt/financial-assistant
git pull
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### 12.2 Ver Logs

```bash
# Backend
docker-compose -f docker-compose.prod.yml logs -f backend

# Worker
docker-compose -f docker-compose.prod.yml logs -f worker

# Todos
docker-compose -f docker-compose.prod.yml logs -f
```

### 12.3 Reiniciar Serviços

```bash
docker-compose -f docker-compose.prod.yml restart backend
docker-compose -f docker-compose.prod.yml restart worker
```

---

## 13. Troubleshooting

### Problema: Backend não inicia

```bash
# Verificar logs
docker-compose -f docker-compose.prod.yml logs backend

# Verificar variáveis de ambiente
docker-compose -f docker-compose.prod.yml exec backend env

# Testar conexão com banco
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"
```

### Problema: Worker não processa jobs

```bash
# Verificar logs do worker
docker-compose -f docker-compose.prod.yml logs worker

# Verificar Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Ver filas
docker-compose -f docker-compose.prod.yml exec redis redis-cli KEYS "*"
```

### Problema: Webhook não recebe mensagens

1. Verificar URL configurada no Twilio
2. Verificar logs do Nginx: `sudo tail -f /var/log/nginx/error.log`
3. Testar endpoint: `curl -X POST https://api.seudominio.com/webhook/whatsapp`
4. Verificar Security Group permite tráfego HTTPS

---

## 14. Custos Estimados

**Infraestrutura AWS (mensal)**:
- EC2 t3.medium (2x): ~$60
- RDS db.t3.small: ~$30
- ElastiCache cache.t3.micro: ~$15
- Load Balancer: ~$20
- Data Transfer: ~$10
- **Total AWS**: ~$135/mês

**Serviços Externos**:
- OpenAI API: ~$50-100/mês
- Twilio WhatsApp: ~$30-50/mês
- Mercado Pago: 4,99% por transação
- **Total Externo**: ~$80-150/mês

**Total Estimado**: ~$215-285/mês (~R$ 1.075-1.425)

---

## 15. Checklist Final

- [ ] RDS criado e acessível
- [ ] ElastiCache criado e acessível
- [ ] EC2 configurado com Docker
- [ ] Código clonado e .env configurado
- [ ] Migrações executadas
- [ ] Planos criados (seed)
- [ ] Nginx configurado
- [ ] SSL configurado (HTTPS)
- [ ] Aplicação rodando (docker-compose up)
- [ ] Webhooks configurados (Twilio + Mercado Pago)
- [ ] Monitoramento configurado (CloudWatch)
- [ ] Backups automáticos configurados
- [ ] Testes realizados (registro, login, WhatsApp)

---

**Deploy concluído! 🚀**

Acesse: `https://seudominio.com`
API: `https://api.seudominio.com/docs`
