import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    <Html lang="pt-BR">
      <Head>
        <meta name="description" content="PayFlow AI é um assistente financeiro conversacional via WhatsApp para criar cobranças, acompanhar recebimentos, enviar links de pagamento e visualizar analytics em um dashboard web." />
        <meta name="keywords" content="WhatsApp, cobranças, IA, dashboard, autônomo, MEI, FastAPI, Next.js, OpenAI" />
        <meta name="author" content="Leonardo Fragoso" />
        <meta name="robots" content="index, follow" />

        {/* Open Graph */}
        <meta property="og:type" content="website" />
        <meta property="og:title" content="PayFlow AI — Assistente Financeiro via WhatsApp" />
        <meta property="og:description" content="Crie cobranças, envie links de pagamento e acompanhe recebimentos via WhatsApp com IA. Dashboard web com analytics e exportação." />
        <meta property="og:site_name" content="PayFlow AI" />
        <meta property="og:locale" content="pt_BR" />

        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="PayFlow AI — Assistente Financeiro via WhatsApp" />
        <meta name="twitter:description" content="Crie cobranças, envie links de pagamento e acompanhe recebimentos via WhatsApp com IA." />

        <link rel="icon" href="/favicon.ico" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  )
}
