# PayFlow AI — Demo Video Script (60-90s)

## Roteiro

### 0-10s — Problema

**Cena:** Tela dividida — planilha confusa de um lado, WhatsApp do outro.

**Narrador:** "Autônomos e MEIs precisam de uma forma simples de cobrar clientes. Planilhas são lentas. Apps financeiros são complexos. E o cliente já está no WhatsApp."

### 10-25s — Landing + Login Demo

**Cena:** Navegação para `http://localhost:3001` → landing page → clique em "Entrar na Demo" → página de login → clique em "Entrar como Demo".

**Narrador:** "PayFlow AI é um assistente financeiro conversacional via WhatsApp. Acesse a demo com um clique — dados de exemplo já carregados."

### 25-45s — Dashboard + Charges

**Cena:** Dashboard carrega → cards de resumo (A Receber, Recebido, Pendentes, Vencidas) → scroll para tabela de cobranças → filtro "Vencidas" → busca por cliente.

**Narrador:** "No dashboard, veja cobranças pendentes, pagas e vencidas. Filtre por status, busque por cliente e acompanhe analytics: taxa de conversão, tempo médio de pagamento e taxa de vencimento."

### 45-60s — Export

**Cena:** Clique em "CSV" → arquivo baixado → clique em "PDF" → arquivo baixado.

**Narrador:** "Exporte cobranças em CSV ou PDF com filtros aplicados — pronto para contabilidade."

### 60-75s — Arquitetura + E2E

**Cena:** Diagrama de arquitetura rápido → terminal com Playwright rodando → testes passando.

**Narrador:** "Backend em FastAPI async, PostgreSQL, Redis para workers e rate limiting. 117 testes no backend, 10 cenários E2E com Playwright. Tudo via Docker Compose."

### 75-90s — Fechamento

**Cena:** Tela final com logo PayFlow AI + link do GitHub.

**Narrador:** "PayFlow AI — projeto de portfólio em modo sandbox. Sem operações bancárias reais. Provider fake por padrão, Mercado Pago sandbox opcional. Código aberto no GitHub."

**Texto na tela:** github.com/LeonardoRFragoso/PayFlow-AI

## Dicas para gravação

- Usar a demo stack (`docker-compose -f docker-compose.demo.yml up`)
- Resolução 1920x1080
- Navegador em modo normal (não incognito, para manter dados demo)
- Zoom do navegador em 100% ou 110% para legibilidade
- Cortar tempos de carregamento se necessário
- Adicionar música de fundo suave (royalty-free)
- Legendas opcionais para acessibilidade

## Screenshots necessários

Gerar antes da gravação:

```bash
cd frontend
npx playwright test e2e/screenshots.spec.ts
```

Screenshots salvos em `docs/assets/`:
- `landing.png`
- `login-demo.png`
- `dashboard-overview.png`
- `charges-table.png`
- `analytics.png`
- `export-pdf.png`
