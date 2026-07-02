import { useEffect, useState, useCallback } from 'react';
import { saasBillingAPI } from '../services/api';
import { getErrorMessage } from '../utils/errorHandler';
import {
  CreditCard, Check, X, AlertTriangle, TrendingUp, Zap, Crown,
  RefreshCw, Loader2, Info,
} from 'lucide-react';

interface Plan {
  code: string;
  name: string;
  description: string;
  price_monthly: string;
  max_charges_per_month: number;
  max_customers: number;
  max_team_members: number;
  max_message_templates: number;
  max_recurring_tasks: number;
  max_whatsapp_messages_per_month: number | null;
  allow_advanced_analytics: boolean;
  allow_pdf_export: boolean;
  allow_ocr: boolean;
  allow_collection_rules: boolean;
  allow_whatsapp_intelligence: boolean;
}

interface SubscriptionSummary {
  subscription: {
    id: number | null;
    status: string;
    billing_provider: string;
    current_period_start: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
  };
  plan: {
    code: string;
    name: string;
    price_monthly: string;
    currency: string;
  };
  usage: {
    charges_created: number;
    customers_created: number;
    templates_created: number;
    recurring_tasks_created: number;
    ocr_documents_analyzed: number;
    pdf_exports_generated: number;
    whatsapp_messages_processed: number;
    collection_followups_generated: number;
  };
  entitlements: Entitlements;
}

interface Entitlements {
  plan: string;
  plan_name: string;
  max_charges_per_month: number;
  max_customers: number;
  max_team_members: number;
  max_message_templates: number;
  max_recurring_tasks: number;
  max_whatsapp_messages_per_month: number | null;
  allow_advanced_analytics: boolean;
  allow_pdf_export: boolean;
  allow_ocr: boolean;
  allow_collection_rules: boolean;
  allow_whatsapp_intelligence: boolean;
}

const PLAN_ICONS: Record<string, React.ReactNode> = {
  free: <Zap className="w-5 h-5 text-gray-500" />,
  starter: <TrendingUp className="w-5 h-5 text-blue-500" />,
  professional: <Crown className="w-5 h-5 text-purple-500" />,
  business: <Crown className="w-5 h-5 text-amber-500" />,
};

const PLAN_COLORS: Record<string, string> = {
  free: 'border-gray-300 dark:border-gray-600',
  starter: 'border-blue-300 dark:border-blue-700',
  professional: 'border-purple-300 dark:border-purple-700',
  business: 'border-amber-300 dark:border-amber-700',
};

const PLAN_BG: Record<string, string> = {
  free: 'bg-gray-50 dark:bg-gray-800/50',
  starter: 'bg-blue-50 dark:bg-blue-900/20',
  professional: 'bg-purple-50 dark:bg-purple-900/20',
  business: 'bg-amber-50 dark:bg-amber-900/20',
};

function formatLimit(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'Ilimitado';
  return value.toLocaleString('pt-BR');
}

function usagePercent(current: number, limit: number | null | undefined): number {
  if (!limit) return 0;
  return Math.min(100, Math.round((current / limit) * 100));
}

function usageColor(percent: number): string {
  if (percent >= 90) return 'bg-red-500';
  if (percent >= 70) return 'bg-yellow-500';
  return 'bg-green-500';
}

export default function BillingSection() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [summary, setSummary] = useState<SubscriptionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState('');

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      const [plansRes, subRes] = await Promise.all([
        saasBillingAPI.getPlans(),
        saasBillingAPI.getSubscription().catch(() => null),
      ]);
      setPlans(plansRes.data || []);
      if (subRes) setSummary(subRes.data);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleChangePlan = async (planCode: string) => {
    setActionLoading(planCode);
    setError('');
    setSuccessMsg('');
    try {
      await saasBillingAPI.changePlan(planCode);
      setSuccessMsg(`Plano alterado para ${planCode} com sucesso!`);
      await fetchAll();
    } catch (e: any) {
      setError(e.response?.data?.detail || getErrorMessage(e));
    } finally {
      setActionLoading(null);
    }
  };

  const handleFakeCheckout = async (planCode: string) => {
    setActionLoading(`checkout-${planCode}`);
    setError('');
    setSuccessMsg('');
    try {
      const res = await saasBillingAPI.fakeCheckout(planCode);
      setSuccessMsg(res.data?.message || `Checkout simulado para ${planCode}!`);
      await fetchAll();
    } catch (e: any) {
      setError(e.response?.data?.detail || getErrorMessage(e));
    } finally {
      setActionLoading(null);
    }
  };

  const handleCancel = async () => {
    setActionLoading('cancel');
    setError('');
    setSuccessMsg('');
    try {
      await saasBillingAPI.cancelSubscription();
      setSuccessMsg('Assinatura cancelada. O plano permanece ativo até o fim do período.');
      await fetchAll();
    } catch (e: any) {
      setError(e.response?.data?.detail || getErrorMessage(e));
    } finally {
      setActionLoading(null);
    }
  };

  const handleReactivate = async () => {
    setActionLoading('reactivate');
    setError('');
    setSuccessMsg('');
    try {
      await saasBillingAPI.reactivateSubscription();
      setSuccessMsg('Assinatura reativada com sucesso!');
      await fetchAll();
    } catch (e: any) {
      setError(e.response?.data?.detail || getErrorMessage(e));
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 mt-6">
        <div className="flex items-center gap-2 mb-4">
          <CreditCard className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Planos &amp; Cobrança</h2>
        </div>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
        </div>
      </div>
    );
  }

  const currentPlanCode = summary?.plan?.code || 'free';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <CreditCard className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Planos &amp; Cobrança</h2>
        </div>
        <button
          onClick={fetchAll}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          title="Atualizar"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {successMsg && (
        <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-start gap-2">
          <Check className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-green-700 dark:text-green-300">{successMsg}</p>
        </div>
      )}

      {/* Current subscription status */}
      {summary && (
        <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Plano atual</p>
              <div className="flex items-center gap-2">
                {PLAN_ICONS[currentPlanCode] || <CreditCard className="w-5 h-5 text-gray-500" />}
                <span className="text-xl font-bold text-gray-900 dark:text-white">
                  {summary.plan.name}
                </span>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                  summary.subscription.status === 'active'
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                    : summary.subscription.status === 'cancelled'
                    ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                    : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
                }`}>
                  {summary.subscription.status === 'active' ? 'Ativo' : summary.subscription.status === 'cancelled' ? 'Cancelado' : summary.subscription.status}
                </span>
              </div>
            </div>
            <div className="flex gap-2">
              {summary.subscription.cancel_at_period_end ? (
                <button
                  onClick={handleReactivate}
                  disabled={actionLoading === 'reactivate'}
                  className="px-3 py-1.5 text-sm font-medium text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-900/40 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/60 transition-colors disabled:opacity-50"
                >
                  {actionLoading === 'reactivate' ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Reativar'}
                </button>
              ) : (
                <button
                  onClick={handleCancel}
                  disabled={actionLoading === 'cancel'}
                  className="px-3 py-1.5 text-sm font-medium text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-900/40 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/60 transition-colors disabled:opacity-50"
                >
                  {actionLoading === 'cancel' ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Cancelar'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Usage meters */}
      {summary && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Uso do período atual</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <UsageMeter
              label="Cobranças"
              current={summary.usage.charges_created}
              limit={summary.entitlements.max_charges_per_month}
            />
            <UsageMeter
              label="Clientes"
              current={summary.usage.customers_created}
              limit={summary.entitlements.max_customers}
            />
            <UsageMeter
              label="Templates"
              current={summary.usage.templates_created}
              limit={summary.entitlements.max_message_templates}
            />
            <UsageMeter
              label="Tarefas recorrentes"
              current={summary.usage.recurring_tasks_created}
              limit={summary.entitlements.max_recurring_tasks}
            />
            <UsageMeter
              label="OCR (documentos)"
              current={summary.usage.ocr_documents_analyzed}
              limit={summary.entitlements.allow_ocr ? undefined : 0}
              blocked={!summary.entitlements.allow_ocr}
            />
            <UsageMeter
              label="Exportações PDF"
              current={summary.usage.pdf_exports_generated}
              limit={summary.entitlements.allow_pdf_export ? undefined : 0}
              blocked={!summary.entitlements.allow_pdf_export}
            />
            <UsageMeter
              label="Mensagens WhatsApp"
              current={summary.usage.whatsapp_messages_processed}
              limit={summary.entitlements.max_whatsapp_messages_per_month}
            />
            <UsageMeter
              label="Follow-ups"
              current={summary.usage.collection_followups_generated}
              limit={summary.entitlements.allow_collection_rules ? undefined : 0}
              blocked={!summary.entitlements.allow_collection_rules}
            />
          </div>
        </div>
      )}

      {/* Plan cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {plans.map((plan) => {
          const isCurrent = plan.code === currentPlanCode;
          const isLoading = actionLoading === plan.code || actionLoading === `checkout-${plan.code}`;
          return (
            <div
              key={plan.code}
              className={`relative rounded-xl border-2 p-4 transition-all ${PLAN_COLORS[plan.code] || 'border-gray-300'} ${PLAN_BG[plan.code] || 'bg-gray-50'} ${isCurrent ? 'ring-2 ring-blue-500' : ''}`}
            >
              {isCurrent && (
                <div className="absolute -top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-blue-600 text-white text-xs font-medium rounded-full">
                  Plano atual
                </div>
              )}
              <div className="flex items-center gap-2 mb-2">
                {PLAN_ICONS[plan.code] || <CreditCard className="w-5 h-5 text-gray-500" />}
                <h4 className="font-bold text-gray-900 dark:text-white">{plan.name}</h4>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{plan.description}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
                R$ {Number(plan.price_monthly).toFixed(2)}
                <span className="text-xs font-normal text-gray-500 dark:text-gray-400">/mês</span>
              </p>
              <ul className="space-y-1 mb-4">
                <FeatureItem included={true} text={`${formatLimit(plan.max_charges_per_month)} cobranças/mês`} />
                <FeatureItem included={true} text={`${formatLimit(plan.max_customers)} clientes`} />
                <FeatureItem included={true} text={`${formatLimit(plan.max_team_members)} membros`} />
                <FeatureItem included={plan.allow_ocr} text="OCR de documentos" />
                <FeatureItem included={plan.allow_pdf_export} text="Exportação PDF" />
                <FeatureItem included={plan.allow_collection_rules} text="Regras de cobrança" />
                <FeatureItem included={plan.allow_advanced_analytics} text="Analytics avançado" />
                <FeatureItem included={plan.allow_whatsapp_intelligence} text="WhatsApp IA" />
              </ul>
              {!isCurrent && (
                <button
                  onClick={() => handleChangePlan(plan.code)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Trocar plano'}
                </button>
              )}
              {!isCurrent && plan.price_monthly !== '0.00' && (
                <button
                  onClick={() => handleFakeCheckout(plan.code)}
                  disabled={isLoading}
                  className="w-full mt-2 px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/30 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Checkout simulado (sandbox)'}
                </button>
              )}
              {isCurrent && (
                <div className="w-full px-3 py-2 text-sm font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 rounded-lg text-center">
                  Seu plano atual
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-2">
        <Info className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-amber-700 dark:text-amber-300">
          Os checkouts são simulados no modo sandbox. Nenhum pagamento real é processado.
          O provedor de cobrança é &quot;fake&quot; para desenvolvimento e demonstração.
        </p>
      </div>
    </div>
  );
}

function UsageMeter({
  label,
  current,
  limit,
  blocked,
}: {
  label: string;
  current: number;
  limit?: number | null;
  blocked?: boolean;
}) {
  if (blocked) {
    return (
      <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</span>
          <X className="w-3 h-3 text-red-500" />
        </div>
        <p className="text-xs text-red-600 dark:text-red-400">Não incluído</p>
      </div>
    );
  }

  const percent = usagePercent(current, limit);
  const color = usageColor(percent);
  const displayLimit = formatLimit(limit);

  return (
    <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {current} / {displayLimit}
        </span>
      </div>
      <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function FeatureItem({ included, text }: { included: boolean; text: string }) {
  return (
    <li className="flex items-center gap-1.5 text-xs">
      {included ? (
        <Check className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
      ) : (
        <X className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      )}
      <span className={included ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'}>
        {text}
      </span>
    </li>
  );
}
