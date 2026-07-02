# PayFlow AI — Release Candidate Checklist

## Backend

- [x] **pytest** — 117 testes passando
- [x] **Alembic** — single head (`e5f6a7b8c9d0`)
- [x] **SECRET_KEY** — requer 64+ caracteres, validado na inicialização
- [x] **Provider padrão** — `fake` (sandbox)
- [x] **Demo mode** — desativado por padrão (`ENABLE_DEMO_MODE=false`)
- [x] **Demo mode nunca em produção** — app falha se `ENVIRONMENT=production` e `ENABLE_DEMO_MODE=true`
- [x] **Mercado Pago** — opt-in apenas (`PAYFLOW_PAYMENT_PROVIDER=mercado_pago`)
- [x] **Mercado Pago bloqueado em demo** — factory rejeita
- [x] **Rate limiting** — habilitado por padrão, Redis + fallback
- [x] **Webhook hardening** — Twilio assinatura obrigatória em prod, MP signature + idempotência
- [x] **Audit logging** — eventos críticos logados com sanitização
- [x] **Sentry** — opcional, redaction de dados sensíveis
- [x] **Admin metrics** — endpoint admin-only, sem dados pessoais
- [x] **Health/ready** — endpoint disponível

## Frontend

- [x] **npm run build** — 12 páginas estáticas geradas com sucesso
- [x] **TypeScript** — tipagem estrita
- [x] **Landing page** — CTAs claros, seções profissionais
- [x] **SEO** — title, meta description, Open Graph
- [x] **robots.txt** — configurado
- [x] **sitemap.xml** — configurado

## Docker

- [x] **docker-compose.yml** — config válida
- [x] **docker-compose.demo.yml** — config válida
- [x] **Dockerfile backend** — paths corrigidos
- [x] **Entrypoint** — respeita command override

## E2E

- [x] **Playwright config** — timeouts, workers=1
- [x] **10 test scenarios** — landing, login, dashboard, cards, charges, filtros, busca, export
- [x] **Seletores estáveis** — `getByRole`, `getByPlaceholder`
- [x] **CI manual** — `workflow_dispatch` sobe demo stack, roda, derruba
- [x] **wait-for-url.sh** — script de espera
- [x] **Screenshots spec** — `screenshots.spec.ts` para gerar imagens

## Segurança

- [x] **Nenhum segredo commitado** — `.env` no `.gitignore`
- [x] **Sem Pix Out** — não implementado
- [x] **Sem saque** — não implementado
- [x] **Sem pagamento real de boleto** — não implementado
- [x] **Sem conta digital** — não implementado
- [x] **Sem BaaS** — não implementado
- [x] **Sem Open Finance** — não implementado
- [x] **Confirmação explícita** — todas as cobranças exigem confirmação
- [x] **JWT auth** — com expiração
- [x] **CORS** — configurado
- [x] **Security headers** — configurados

## Documentação

- [x] **README.md** — revisado, badges, seções completas
- [x] **CASE_STUDY.md** — case study técnico
- [x] **RELEASE_NOTES.md** — release notes por sprint
- [x] **RELEASE_CANDIDATE_CHECKLIST.md** — este checklist
- [x] **OBSERVABILITY.md** — Sentry, audit logging, admin metrics
- [x] **SECURITY_HARDENING.md** — demo mode, rate limiting, webhook hardening
- [x] **E2E_TESTING.md** — Playwright setup, CI, limitações
- [x] **ARCHITECTURE.md** — arquitetura detalhada
- [x] **LINKEDIN_LAUNCH_POST.md** — post LinkedIn
- [x] **DEMO_VIDEO_SCRIPT.md** — roteiro de vídeo demo

## Screenshots

- [ ] `docs/assets/landing.png` — gerar via `screenshots.spec.ts`
- [ ] `docs/assets/login-demo.png` — gerar via `screenshots.spec.ts`
- [ ] `docs/assets/dashboard-overview.png` — gerar via `screenshots.spec.ts`
- [ ] `docs/assets/charges-table.png` — gerar via `screenshots.spec.ts`
- [ ] `docs/assets/analytics.png` — gerar via `screenshots.spec.ts`
- [ ] `docs/assets/export-pdf.png` — gerar via `screenshots.spec.ts`
- [ ] `docs/assets/e2e-report.png` — gerar via Playwright HTML report

> Screenshots são gerados rodando `npx playwright test e2e/screenshots.spec.ts` contra a demo stack.

## Validação final

```bash
# Backend
cd backend && source .venv/bin/activate
pytest -v tests
alembic heads

# Frontend
cd frontend && npm run build

# Docker
docker-compose config -q
docker-compose -f docker-compose.demo.yml config -q

# E2E (se Docker disponível)
docker-compose -f docker-compose.demo.yml up -d --build
./scripts/wait-for-url.sh http://localhost:8001/health/ready 120
./scripts/wait-for-url.sh http://localhost:3001 120
cd frontend && E2E_BASE_URL=http://localhost:3001 npm run test:e2e
cd .. && docker-compose -f docker-compose.demo.yml down -v
```
