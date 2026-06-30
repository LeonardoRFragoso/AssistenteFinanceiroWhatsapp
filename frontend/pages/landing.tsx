import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { 
  Smartphone, 
  TrendingUp, 
  Shield, 
  Zap, 
  Check,
  ArrowRight,
  MessageCircle,
  BarChart3,
  Bell,
  Receipt
} from 'lucide-react';

export default function Landing() {
  const router = useRouter();
  const [selectedPlan, setSelectedPlan] = useState<'free' | 'pro'>('pro');

  const plans = {
    free: {
      name: 'Gratuito',
      price: 0,
      features: [
        '20 transações por mês',
        'WhatsApp integrado',
        'Dashboard web',
        'Insights básicos',
        'Suporte por email'
      ]
    },
    pro: {
      name: 'Pro',
      price: 29.90,
      features: [
        'Transações ilimitadas',
        'WhatsApp integrado',
        'Dashboard avançado',
        'Insights com IA',
        'Suporte prioritário',
        'Exportação PDF',
        'Categorias personalizadas'
      ]
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-50">
      <nav className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Smartphone className="w-8 h-8 text-primary-600" />
              <span className="text-xl font-bold text-gray-900">PayFlow AI</span>
            </div>
            <div className="flex gap-4">
              <Link href="/login" className="text-gray-700 hover:text-gray-900 font-medium">
                Entrar
              </Link>
              <Link 
                href="/register" 
                className="bg-primary-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-primary-700 transition-colors"
              >
                Começar Grátis
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-16">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            PayFlow AI
            <br />
            <span className="text-primary-600">cobranças pelo WhatsApp</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Crie cobranças, links de pagamento e acompanhe receitas de clientes
            conversando naturalmente pelo WhatsApp. Ideal para autônomos, MEIs e pequenos negócios.
          </p>
          <div className="flex gap-4 justify-center">
            <Link 
              href="/register"
              className="bg-primary-600 text-white px-8 py-4 rounded-lg font-bold text-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
            >
              Começar Agora
              <ArrowRight className="w-5 h-5" />
            </Link>
            <a 
              href="#como-funciona"
              className="bg-white text-primary-600 border-2 border-primary-600 px-8 py-4 rounded-lg font-bold text-lg hover:bg-primary-50 transition-colors"
            >
              Ver Como Funciona
            </a>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8 mb-20">
          <div className="bg-white p-8 rounded-2xl shadow-lg">
            <div className="bg-primary-100 w-16 h-16 rounded-full flex items-center justify-center mb-4">
              <MessageCircle className="w-8 h-8 text-primary-600" />
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">WhatsApp Integrado</h3>
            <p className="text-gray-600">
              Envie mensagens naturais como "Gastei R$ 50 com almoço" e pronto!
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg">
            <div className="bg-primary-100 w-16 h-16 rounded-full flex items-center justify-center mb-4">
              <BarChart3 className="w-8 h-8 text-primary-600" />
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">Insights com IA</h3>
            <p className="text-gray-600">
              Receba análises automáticas sobre seus gastos e dicas personalizadas.
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg">
            <div className="bg-primary-100 w-16 h-16 rounded-full flex items-center justify-center mb-4">
              <Receipt className="w-8 h-8 text-primary-600" />
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">Cobranças Pix</h3>
            <p className="text-gray-600">
              Crie cobranças e links de pagamento pelo WhatsApp e receba quando seus clientes pagarem.
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg">
            <div className="bg-primary-100 w-16 h-16 rounded-full flex items-center justify-center mb-4">
              <Shield className="w-8 h-8 text-primary-600" />
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">100% Seguro</h3>
            <p className="text-gray-600">
              Seus dados são criptografados e protegidos com tecnologia de ponta.
            </p>
          </div>
        </div>
      </section>

      <section id="como-funciona" className="bg-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl font-bold text-center text-gray-900 mb-16">
            Como Funciona
          </h2>
          
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="space-y-8">
                <div className="flex gap-4">
                  <div className="bg-primary-600 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold flex-shrink-0">
                    1
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Cadastre-se</h3>
                    <p className="text-gray-600">
                      Crie sua conta em menos de 1 minuto. É grátis!
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="bg-primary-600 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold flex-shrink-0">
                    2
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Conecte o WhatsApp</h3>
                    <p className="text-gray-600">
                      Adicione nosso número e comece a conversar.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="bg-primary-600 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold flex-shrink-0">
                    3
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Registre suas finanças</h3>
                    <p className="text-gray-600">
                      Envie mensagens como "Gastei R$ 100 no mercado" e deixe a IA fazer o resto.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="bg-primary-600 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold flex-shrink-0">
                    4
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Receba Insights</h3>
                    <p className="text-gray-600">
                      Veja análises automáticas e tome decisões mais inteligentes.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-primary-100 to-primary-200 p-8 rounded-2xl">
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <div className="flex items-start gap-3 mb-4">
                  <div className="bg-green-500 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold">
                    V
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-500 mb-1">Você</p>
                    <p className="text-gray-900">Gastei R$ 50 com almoço</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="bg-primary-600 w-10 h-10 rounded-full flex items-center justify-center">
                    <Smartphone className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-500 mb-1">Assistente</p>
                    <div className="bg-primary-50 rounded-lg p-3">
                      <p className="text-gray-900 mb-2">✅ Despesa registrada!</p>
                      <p className="text-sm text-gray-600">
                        💸 Valor: R$ 50,00<br />
                        📁 Categoria: Alimentação<br />
                        📅 Data: 17/02/2026
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl font-bold text-center text-gray-900 mb-4">
            Escolha seu Plano
          </h2>
          <p className="text-center text-gray-600 mb-12">
            Comece grátis e faça upgrade quando precisar
          </p>

          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <div className="bg-white rounded-2xl shadow-lg p-8 border-2 border-gray-200">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">{plans.free.name}</h3>
              <div className="mb-6">
                <span className="text-4xl font-bold text-gray-900">R$ {plans.free.price}</span>
                <span className="text-gray-600">/mês</span>
              </div>
              <ul className="space-y-3 mb-8">
                {plans.free.features.map((feature, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <Check className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className="block w-full bg-gray-100 text-gray-900 py-3 rounded-lg font-semibold text-center hover:bg-gray-200 transition-colors"
              >
                Começar Grátis
              </Link>
            </div>

            <div className="bg-gradient-to-br from-primary-600 to-primary-700 rounded-2xl shadow-xl p-8 border-2 border-primary-600 relative">
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-yellow-400 text-gray-900 px-4 py-1 rounded-full text-sm font-bold">
                MAIS POPULAR
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">{plans.pro.name}</h3>
              <div className="mb-6">
                <span className="text-4xl font-bold text-white">R$ {plans.pro.price}</span>
                <span className="text-primary-100">/mês</span>
              </div>
              <ul className="space-y-3 mb-8">
                {plans.pro.features.map((feature, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <Check className="w-5 h-5 text-yellow-400" />
                    <span className="text-white">{feature}</span>
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className="block w-full bg-white text-primary-600 py-3 rounded-lg font-bold text-center hover:bg-primary-50 transition-colors"
              >
                Começar Agora
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Smartphone className="w-6 h-6" />
                <span className="font-bold">Assistente Financeiro</span>
              </div>
              <p className="text-gray-400">
                Controle suas finanças de forma simples e inteligente pelo WhatsApp.
              </p>
            </div>
            <div>
              <h4 className="font-bold mb-4">Links</h4>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="/login" className="hover:text-white">Login</Link></li>
                <li><Link href="/register" className="hover:text-white">Cadastro</Link></li>
                <li><a href="#como-funciona" className="hover:text-white">Como Funciona</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Contato</h4>
              <p className="text-gray-400">
                suporte@assistentefinanceiro.com.br
              </p>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2026 Assistente Financeiro. Todos os direitos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
