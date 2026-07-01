import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Wallet,
  MessageCircle,
  BarChart3,
  Bell,
  Receipt,
  Shield,
  Zap,
  ArrowRight,
  Check,
  Smartphone,
  FileText,
  TrendingUp,
  Sparkles,
} from 'lucide-react';

const ENABLE_DEMO = process.env.NEXT_PUBLIC_ENABLE_DEMO_MODE === 'true';

export default function Home() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-gray-950 dark:to-gray-900">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <Wallet className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900 dark:text-white">PayFlow AI</span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/login"
                className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
              >
                Entrar
              </Link>
              {ENABLE_DEMO ? (
                <button
                  onClick={() => router.push('/login')}
                  className="text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-2 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all"
                >
                  Demo
                </button>
              ) : (
                <Link
                  href="/register"
                  className="text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-2 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all"
                >
                  Cadastrar
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden py-20 sm:py-28">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-gradient-to-br from-blue-400/20 to-purple-400/20 rounded-full blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-gradient-to-tr from-indigo-400/20 to-pink-400/20 rounded-full blur-3xl"></div>
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm font-medium mb-6">
              <Zap className="w-4 h-4" />
              Assistente Financeiro via WhatsApp
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-gray-900 dark:text-white tracking-tight">
              PayFlow AI
            </h1>
            <p className="mt-6 text-xl sm:text-2xl text-gray-600 dark:text-gray-400 font-medium">
              Cobranças inteligentes via WhatsApp para autônomos, MEIs e pequenos negócios
            </p>
            <p className="mt-4 text-base text-gray-500 dark:text-gray-500 max-w-2xl mx-auto">
              Crie cobranças, envie links de pagamento, acompanhe recebimentos e receba lembretes automáticos em um dashboard simples.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
              {ENABLE_DEMO ? (
                <button
                  onClick={() => router.push('/login')}
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 font-semibold shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
                >
                  <Sparkles className="w-5 h-5" />
                  Entrar na demo
                </button>
              ) : (
                <Link
                  href="/register"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 font-semibold shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
                >
                  Começar grátis
                  <ArrowRight className="w-5 h-5" />
                </Link>
              )}
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 font-semibold transition-all"
              >
                <BarChart3 className="w-5 h-5" />
                Ver dashboard
              </Link>
            </div>
            <p className="mt-6 text-xs text-gray-400 dark:text-gray-600">
              Projeto em modo sandbox/demo — sem operações bancárias reais
            </p>
          </div>
        </div>
      </section>

      {/* Como funciona */}
      <section className="py-16 bg-white dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-12">Como funciona</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center mb-4">
                <MessageCircle className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">1. Conversa no WhatsApp</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Envie mensagens em linguagem natural como "Cobre R$ 150 do João pelo serviço de design" e a IA cria a cobrança.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 mx-auto bg-purple-100 dark:bg-purple-900/30 rounded-2xl flex items-center justify-center mb-4">
                <Receipt className="w-8 h-8 text-purple-600 dark:text-purple-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">2. Link de pagamento</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                O sistema gera um link de pagamento e envia para o cliente via WhatsApp com confirmação do usuário.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 mx-auto bg-indigo-100 dark:bg-indigo-900/30 rounded-2xl flex items-center justify-center mb-4">
                <BarChart3 className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">3. Dashboard web</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Acompanhe recebimentos, cobranças pendentes, vencidas e analytics no dashboard web com exportação CSV/PDF.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Funcionalidades */}
      <section className="py-16 bg-gray-50 dark:bg-gray-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-12">Funcionalidades</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: MessageCircle, title: 'IA via WhatsApp', desc: 'Cobranças com linguagem natural em português' },
              { icon: Receipt, title: 'Cobranças com vencimento', desc: 'Defina datas e receba lembretes automáticos' },
              { icon: Bell, title: 'Lembretes automáticos', desc: 'Notificações de vencimento e cobranças atrasadas' },
              { icon: BarChart3, title: 'Analytics e relatórios', desc: 'Taxa de conversão, tempo médio de pagamento' },
              { icon: FileText, title: 'Exportação CSV/PDF', desc: 'Exporte cobranças com filtros de status e data' },
              { icon: Shield, title: 'Confirmação explícita', desc: 'Toda cobrança exige confirmação do usuário' },
            ].map((f, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center mb-4">
                  <f.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">{f.title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Segurança */}
      <section className="py-16 bg-white dark:bg-gray-900">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-8">Segurança</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-start gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Provider padrão <strong>fake</strong> — nenhuma cobrança real é processada</p>
            </div>
            <div className="flex items-start gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Mercado Pago sandbox apenas com opt-in explícito</p>
            </div>
            <div className="flex items-start gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Confirmação explícita para todas as cobranças via WhatsApp</p>
            </div>
            <div className="flex items-start gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700 dark:text-gray-300">JWT auth, rate limiting e security headers</p>
            </div>
            <div className="flex items-start gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Sem Pix Out, sem saque, sem conta digital</p>
            </div>
            <div className="flex items-start gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Segredos via .env, nunca commitados</p>
            </div>
          </div>
        </div>
      </section>

      {/* Stack técnica */}
      <section className="py-16 bg-gray-50 dark:bg-gray-950">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-8">Stack técnica</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { name: 'Python + FastAPI', desc: 'Backend async' },
              { name: 'Next.js + TypeScript', desc: 'Frontend' },
              { name: 'PostgreSQL + SQLAlchemy', desc: 'Database' },
              { name: 'Redis + RQ', desc: 'Queue/Workers' },
              { name: 'OpenAI GPT-4o', desc: 'NLP/IA' },
              { name: 'Twilio WhatsApp', desc: 'Mensageria' },
              { name: 'Docker Compose', desc: 'Infra' },
              { name: 'ReportLab', desc: 'PDF export' },
            ].map((tech, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center border border-gray-200 dark:border-gray-700">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{tech.name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{tech.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Roadmap */}
      <section className="py-16 bg-white dark:bg-gray-900">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-8">Roadmap</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">Sprint 1-2: Transações, cobranças e dashboard</span>
            </div>
            <div className="flex items-center gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">Sprint 3: Mercado Pago sandbox, lembretes, CSV export</span>
            </div>
            <div className="flex items-center gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">Sprint 4: Paginação, analytics, PDF export, testes de integração</span>
            </div>
            <div className="flex items-center gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">Sprint 4.1: Filtros derivados (overdue), date range inclusivo</span>
            </div>
            <div className="flex items-center gap-3">
              <Check className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">Sprint 5: Demo mode, landing page, deploy readiness</span>
            </div>
            <div className="flex items-center gap-3">
              <ArrowRight className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
              <span className="text-sm text-gray-500 dark:text-gray-400">Próximo: Testes E2E, observabilidade, multi-tenant</span>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Pronto para experimentar?</h2>
          <p className="text-blue-100 mb-8">Acesse a demo com dados de exemplo ou crie sua conta</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {ENABLE_DEMO ? (
              <button
                onClick={() => router.push('/login')}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-blue-700 bg-white hover:bg-blue-50 font-semibold shadow-lg transition-all"
              >
                <Smartphone className="w-5 h-5" />
                Entrar na demo
              </button>
            ) : (
              <Link
                href="/register"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-blue-700 bg-white hover:bg-blue-50 font-semibold shadow-lg transition-all"
              >
                Criar conta grátis
                <ArrowRight className="w-5 h-5" />
              </Link>
            )}
            <Link
              href="/login"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-white border border-white/30 hover:bg-white/10 font-semibold transition-all"
            >
              Já tenho conta
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 bg-gray-900 dark:bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
              <Wallet className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-white">PayFlow AI</span>
          </div>
          <p className="text-sm text-gray-400 max-w-2xl mx-auto">
            Projeto de portfólio em modo sandbox. Não é uma instituição financeira.
            Não oferece conta digital, Pix Out, saque ou pagamento de boletos.
          </p>
          <p className="text-xs text-gray-600 mt-4">
            © 2025 PayFlow AI — Leonardo Fragoso
          </p>
        </div>
      </footer>
    </div>
  );
}
