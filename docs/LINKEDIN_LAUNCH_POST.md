# PayFlow AI — LinkedIn Launch Post

## Post (PT-BR)

---

Após meses de desenvolvimento iterativo, estou compartilhando o PayFlow AI — um assistente financeiro conversacional via WhatsApp para gestão de cobranças.

🔗 https://github.com/LeonardoRFragoso/PayFlow-AI

**O problema:** Autônomos, MEIs e pequenos negócios precisam de uma forma simples de cobrar clientes e acompanhar pagamentos. Soluções existentes são complexas e não aproveitam o canal onde o pequeno negócio já está: o WhatsApp.

**A solução:** Um SaaS que combina IA (OpenAI GPT-4o), WhatsApp (Twilio) e um dashboard web (Next.js) para:
- Criar cobranças com linguagem natural ("Cobre R$ 150 do João pelo serviço de design")
- Enviar links de pagamento diretamente ao cliente
- Acompanhar status (pendente, pago, vencido) no dashboard
- Receber lembretes automáticos de vencimento
- Exportar dados em CSV/PDF

**Stack técnica:**
- Backend: Python, FastAPI (async), SQLAlchemy 2.0, PostgreSQL, Redis + RQ
- Frontend: Next.js, TypeScript, TailwindCSS
- IA: OpenAI GPT-4o para NLP
- Mensageria: Twilio WhatsApp Business API
- Infra: Docker Compose
- Testes: pytest (117 testes), Playwright E2E (10 cenários)

**Decisões de segurança que tomei a sério:**
- Provider padrão é "fake" — nenhuma cobrança real é processada sem opt-in explícito
- Mercado Pago sandbox apenas com credenciais explícitas
- Confirmação explícita do usuário antes de qualquer cobrança
- Rate limiting por usuário e por IP (Redis + fallback in-memory)
- Validação de assinatura de webhooks (Twilio e Mercado Pago)
- Idempotência de webhooks para evitar processamento duplicado
- Sentry opcional com redaction de dados sensíveis
- Audit logging estruturado para eventos críticos
- Demo mode nunca roda em produção (app falha na inicialização)

**Evolução por sprints:**
- Sprint 1-2: Foundation — cobranças, dashboard, lembretes
- Sprint 3-4: Mercado Pago sandbox, analytics, PDF, testes de integração
- Sprint 5-5.1: Demo mode, landing page, hardening de segurança
- Sprint 6-6.1: E2E com Playwright, observabilidade (Sentry), rate limiting, webhook hardening, CI stabilization

**O que NÃO é:**
Não é uma instituição financeira. Não oferece conta digital, Pix Out, saque ou pagamento de boletos. É um projeto sandbox/demo com provider fake por padrão.

O projeto está pronto para avaliação técnica. Demo disponível via Docker Compose com dados pré-populados.

#softwareengineering #python #fastapi #nextjs #typescript #openai #whatsapp #fintech #portfolio #opensource

---

## Notas para publicação

- Adaptar o tom conforme seu estilo pessoal
- Incluir screenshots do dashboard e landing page se possível
- Considerar adicionar um breve vídeo demo (60-90s) — ver `docs/DEMO_VIDEO_SCRIPT.md`
- O link do GitHub deve ser o primeiro ou segundo parágrafo para visibilidade
- Hashtags podem ser ajustadas conforme audiência
