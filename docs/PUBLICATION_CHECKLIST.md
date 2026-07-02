# PayFlow AI — Publication Checklist

## README

- [x] Badges carregando (Python, FastAPI, Next.js, PostgreSQL, Redis, Docker, Tests, E2E)
- [x] Screenshots renderizando (landing, login-demo, dashboard, charges-table, analytics, export, e2e-report)
- [x] Links internos funcionando (ver tabela abaixo)
- [x] Instruções de demo corretas (docker-compose.demo.yml, portas 3001/8001)
- [x] Nenhuma promessa de operação bancária sensível
- [x] Provider fake como default documentado
- [x] Demo mode desativado por padrão documentado

### Links internos verificados

| Link | Existe |
|---|---|
| `docs/CASE_STUDY.md` | ✅ |
| `docs/RELEASE_NOTES.md` | ✅ |
| `docs/RELEASE_CANDIDATE_CHECKLIST.md` | ✅ |
| `docs/PUBLICATION_CHECKLIST.md` | ✅ |
| `docs/ARCHITECTURE.md` | ✅ |
| `docs/DEPLOYMENT_GUIDE.md` | ✅ |
| `docs/E2E_TESTING.md` | ✅ |
| `docs/OBSERVABILITY.md` | ✅ |
| `docs/SECURITY_HARDENING.md` | ✅ |
| `docs/LINKEDIN_LAUNCH_POST.md` | ✅ |
| `docs/DEMO_VIDEO_SCRIPT.md` | ✅ |

## Favicon

- [x] `frontend/public/favicon.ico` existe (4286 bytes)
- [x] `frontend/public/favicon.svg` existe (493 bytes)
- [x] `_document.tsx` referencia ambos os formatos

## Screenshots

- [x] `docs/assets/landing.png`
- [x] `docs/assets/login-demo.png`
- [x] `docs/assets/dashboard-overview.png`
- [x] `docs/assets/charges-table.png`
- [x] `docs/assets/analytics.png`
- [x] `docs/assets/export-pdf.png`
- [x] `docs/assets/e2e-report.png`

## Backend

- [x] **pytest** — 117 testes passando
- [x] **Alembic** — single head (`e5f6a7b8c9d0`)
- [x] **SECRET_KEY** — requer 64+ caracteres
- [x] **Provider padrão** — `fake`
- [x] **Demo mode** — desativado por padrão
- [x] **Demo mode nunca em produção** — app falha se `ENVIRONMENT=production` e `ENABLE_DEMO_MODE=true`
- [x] **Mercado Pago** — opt-in apenas, bloqueado em demo mode
- [x] **Rate limiting** — habilitado por padrão
- [x] **Webhook hardening** — assinatura validada
- [x] **Audit logging** — eventos críticos logados
- [x] **Sentry** — opcional, redaction de dados

## Frontend

- [x] **npm run build** — 12 páginas estáticas geradas
- [x] **TypeScript** — tipagem estrita
- [x] **Landing page** — CTAs claros, seções profissionais
- [x] **SEO** — title, meta description, Open Graph, Twitter Card
- [x] **robots.txt** — configurado
- [x] **sitemap.xml** — configurado
- [x] **favicon** — ICO + SVG

## Docker

- [x] **docker-compose.yml** — config válida
- [x] **docker-compose.demo.yml** — config válida
- [x] **Dockerfile backend** — paths corrigidos
- [x] **Entrypoint** — respeita command override

## E2E

- [x] **Playwright config** — timeouts, workers=1, retries
- [x] **10 test scenarios** — landing, login, dashboard, cards, charges, filtros, busca, export
- [x] **Seletores estáveis** — `getByRole`, `getByPlaceholder`
- [x] **waitForDashboardReady** — helper robusto que aguarda elementos específicos
- [x] **CI manual** — `workflow_dispatch` sobe demo stack, roda, derruba
- [x] **Screenshots spec** — `screenshots.spec.ts` para gerar imagens
- [x] **E2E report** — screenshot/placeholder em `docs/assets/e2e-report.png`

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

## Publicação

- [x] README revisado
- [x] Screenshots OK
- [x] Favicon OK
- [x] Backend tests OK (117 passed)
- [x] Frontend build OK (12 pages)
- [x] docker-compose config OK
- [x] docker-compose.demo config OK
- [x] E2E OK (10 passed, retries configurados)
- [x] Nenhum segredo commitado
- [x] Demo mode seguro (off por padrão, nunca em produção)
- [x] Provider fake default
- [x] LinkedIn post revisado
- [x] Vídeo demo pronto para gravação (roteiro em `docs/DEMO_VIDEO_SCRIPT.md`)

## Tag Git sugerida

```bash
git tag -a v1.0.0-rc1 -m "PayFlow AI release candidate"
git push origin v1.0.0-rc1
```

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
