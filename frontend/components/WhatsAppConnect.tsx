import { useState } from 'react';
import { MessageCircle, Copy, Check, QrCode } from 'lucide-react';

export default function WhatsAppConnect() {
  const [copied, setCopied] = useState(false);
  const whatsappNumber = '+1 415 523 8886';
  const joinCode = 'join steady-feature';

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-2xl p-6 border border-green-200 dark:border-green-800 shadow-lg">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-green-600 rounded-xl">
          <MessageCircle className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">
            📱 Como usar o WhatsApp
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Envie mensagens como <span className="font-semibold">"Gastei R$ 50 com almoço"</span> ou{' '}
            <span className="font-semibold">"Quanto gastei este mês?"</span> para registrar e consultar suas finanças rapidamente.
          </p>
        </div>
      </div>

      <div className="mt-6 grid md:grid-cols-2 gap-6">
        {/* QR Code Section */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <QrCode className="w-5 h-5 text-green-600" />
            <h4 className="font-semibold text-gray-900 dark:text-gray-100">
              Escaneie o QR Code
            </h4>
          </div>
          <div className="bg-white p-4 rounded-lg inline-block mb-4">
            <img
              src="/qrcode-wpp.svg"
              alt="WhatsApp QR Code"
              width={200}
              height={200}
              className="mx-auto"
            />
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Abra o WhatsApp e escaneie este código
          </p>
        </div>

        {/* Manual Instructions */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6">
          <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Ou envie manualmente:
          </h4>
          
          <div className="space-y-4">
            {/* Step 1 */}
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                1. Adicione o número
              </label>
              <div className="mt-1 flex items-center gap-2">
                <div className="flex-1 bg-gray-50 dark:bg-gray-700 rounded-lg px-4 py-3 font-mono text-sm text-gray-900 dark:text-gray-100">
                  {whatsappNumber}
                </div>
                <button
                  onClick={() => handleCopy(whatsappNumber)}
                  className="p-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                  title="Copiar número"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Step 2 */}
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                2. Envie esta mensagem
              </label>
              <div className="mt-1 flex items-center gap-2">
                <div className="flex-1 bg-gray-50 dark:bg-gray-700 rounded-lg px-4 py-3 font-mono text-sm text-gray-900 dark:text-gray-100">
                  {joinCode}
                </div>
                <button
                  onClick={() => handleCopy(joinCode)}
                  className="p-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                  title="Copiar código"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Step 3 */}
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <span className="font-semibold text-green-600">3. Pronto!</span> Você receberá uma confirmação e poderá começar a usar o assistente.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Examples */}
      <div className="mt-6 bg-white dark:bg-gray-800 rounded-xl p-4">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          💬 Exemplos de comandos:
        </h4>
        <div className="grid sm:grid-cols-2 gap-2 text-sm">
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2 text-gray-700 dark:text-gray-300">
            "Gastei R$ 50 com almoço"
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2 text-gray-700 dark:text-gray-300">
            "Quanto gastei este mês?"
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2 text-gray-700 dark:text-gray-300">
            "Lembrar de pagar conta amanhã"
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2 text-gray-700 dark:text-gray-300">
            "Qual meu saldo?"
          </div>
        </div>
      </div>
    </div>
  );
}
