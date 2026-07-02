import { useEffect, useState } from 'react';
import { analyticsAPI } from '../services/api';
import { getErrorMessage } from '../utils/errorHandler';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import {
  TrendingUp, TrendingDown, DollarSign, Clock, AlertTriangle,
  Users, Download, FileText, BarChart3, Lightbulb, Activity,
} from 'lucide-react';

interface Overview {
  total_billed: number;
  total_paid: number;
  total_pending: number;
  total_overdue: number;
  collection_rate: number;
  overdue_rate: number;
  average_payment_time_days: number | null;
  average_delay_days: number | null;
  active_customers: number;
  overdue_customers: number;
  followups_drafted: number;
  followups_sent: number;
  total_charges: number;
  paid_count: number;
  pending_count: number;
  overdue_count: number;
}

interface TrendItem {
  month: string;
  billed_amount: number;
  paid_amount: number;
  pending_amount: number;
  overdue_amount: number;
  charges_created: number;
  charges_paid: number;
  collection_rate: number;
}

interface AgingBucket {
  bucket: string;
  count: number;
  amount: number;
  percentage: number;
}

interface AgingData {
  total_overdue: number;
  total_overdue_amount: number;
  buckets: AgingBucket[];
}

interface CustomerPerfItem {
  customer_name: string;
  operational_status: string;
  total_billed: number;
  total_paid: number;
  total_pending: number;
  total_overdue: number;
  average_payment_delay_days: number;
  charges_count: number;
  last_payment_at: string | null;
  suggested_action: string;
}

interface CollectionPerf {
  total_drafts: number;
  drafts_by_tone: Record<string, number>;
  drafts_by_status: Record<string, number>;
  customers_contacted: number;
  followups_this_month: number;
  charges_with_followup: number;
  charges_paid_after_followup: number;
  estimated_recovered_amount: number;
  insufficient_data: boolean;
}

const PERIOD_OPTIONS = [
  { label: '30 dias', value: '30' },
  { label: '90 dias', value: '90' },
  { label: '6 meses', value: '180' },
  { label: '12 meses', value: '365' },
];

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  good_payer: { label: 'Bom pagador', color: 'text-green-600' },
  late_payer: { label: 'Atrasa', color: 'text-yellow-600' },
  frequent_late: { label: 'Atrasa muito', color: 'text-red-600' },
  new_customer: { label: 'Novo', color: 'text-blue-600' },
  inactive_customer: { label: 'Inativo', color: 'text-gray-500' },
};

const ACTION_LABELS: Record<string, string> = {
  send_friendly_reminder: 'Enviar lembrete amigável',
  review_payment_terms: 'Revisar termos de pagamento',
  thank_customer: 'Agradecer cliente',
  monitor: 'Monitorar',
  no_action: 'Sem ação necessária',
};

export default function AdvancedAnalyticsSection() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [trends, setTrends] = useState<TrendItem[]>([]);
  const [aging, setAging] = useState<AgingData | null>(null);
  const [customerPerf, setCustomerPerf] = useState<CustomerPerfItem[]>([]);
  const [collectionPerf, setCollectionPerf] = useState<CollectionPerf | null>(null);
  const [insights, setInsights] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState('90');
  const [exportingCSV, setExportingCSV] = useState(false);
  const [exportingPDF, setExportingPDF] = useState(false);

  useEffect(() => {
    loadAnalytics();
  }, [period]);

  const getDateRange = () => {
    const days = parseInt(period);
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    return {
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
    };
  };

  const loadAnalytics = async () => {
    setLoading(true);
    setError('');
    try {
      const range = getDateRange();
      const [ovRes, trendsRes, agingRes, custRes, collRes, insightsRes] = await Promise.all([
        analyticsAPI.getOverview(range),
        analyticsAPI.getMonthlyTrends(6),
        analyticsAPI.getAging(),
        analyticsAPI.getCustomerPerformance(10),
        analyticsAPI.getCollectionPerformance(),
        analyticsAPI.getInsights(range),
      ]);
      setOverview(ovRes.data);
      setTrends(trendsRes.data);
      setAging(agingRes.data);
      setCustomerPerf(custRes.data);
      setCollectionPerf(collRes.data);
      setInsights(insightsRes.data.insights || []);
    } catch (e) {
      setError(getErrorMessage(e));
    }
    setLoading(false);
  };

  const handleExportCSV = async () => {
    setExportingCSV(true);
    try {
      const range = getDateRange();
      const res = await analyticsAPI.exportCSV(range);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_export_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(getErrorMessage(e));
    }
    setExportingCSV(false);
  };

  const handleExportPDF = async () => {
    setExportingPDF(true);
    try {
      const range = getDateRange();
      const res = await analyticsAPI.exportPDF(range);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_report_${new Date().toISOString().split('T')[0]}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(getErrorMessage(e));
    }
    setExportingPDF(false);
  };

  const formatCurrency = (v: number) => `R$ ${v.toFixed(2)}`;

  if (loading) {
    return (
      <div data-testid="advanced-analytics-section" className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mt-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Analytics Avançado</h2>
        <p className="text-gray-500 dark:text-gray-400">Carregando...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="advanced-analytics-section" className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mt-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Analytics Avançado</h2>
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  return (
    <div data-testid="advanced-analytics-section" className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mt-6">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-emerald-600" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Analytics Avançado</h2>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            data-testid="analytics-period-filter"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            {PERIOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button
            data-testid="analytics-export-csv"
            onClick={handleExportCSV}
            disabled={exportingCSV}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            CSV
          </button>
          <button
            data-testid="analytics-export-pdf"
            onClick={handleExportPDF}
            disabled={exportingPDF}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50"
          >
            <FileText className="w-4 h-4" />
            PDF
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      {overview && (
        <div data-testid="analytics-overview-cards" className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-4 h-4 text-emerald-600" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Total cobrado</span>
            </div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{formatCurrency(overview.total_billed)}</p>
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-green-600" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Recebido</span>
            </div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{formatCurrency(overview.total_paid)}</p>
          </div>
          <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-yellow-600" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Pendente</span>
            </div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{formatCurrency(overview.total_pending)}</p>
          </div>
          <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Vencido</span>
            </div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{formatCurrency(overview.total_overdue)}</p>
          </div>
        </div>
      )}

      {/* Rate badges */}
      {overview && (
        <div className="flex flex-wrap gap-3 mb-6">
          <div className="px-3 py-1.5 bg-emerald-100 dark:bg-emerald-900/30 rounded-full text-sm">
            <span className="text-gray-500 dark:text-gray-400">Taxa de recebimento: </span>
            <span className="font-bold text-emerald-700 dark:text-emerald-400">{overview.collection_rate}%</span>
          </div>
          <div className="px-3 py-1.5 bg-red-100 dark:bg-red-900/30 rounded-full text-sm">
            <span className="text-gray-500 dark:text-gray-400">Taxa de vencimento: </span>
            <span className="font-bold text-red-700 dark:text-red-400">{overview.overdue_rate}%</span>
          </div>
          {overview.average_payment_time_days !== null && (
            <div className="px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-full text-sm">
              <span className="text-gray-500 dark:text-gray-400">Tempo médio: </span>
              <span className="font-bold text-blue-700 dark:text-blue-400">{overview.average_payment_time_days}d</span>
            </div>
          )}
          {overview.average_delay_days !== null && (
            <div className="px-3 py-1.5 bg-orange-100 dark:bg-orange-900/30 rounded-full text-sm">
              <span className="text-gray-500 dark:text-gray-400">Atraso médio: </span>
              <span className="font-bold text-orange-700 dark:text-orange-400">{overview.average_delay_days}d</span>
            </div>
          )}
          <div className="px-3 py-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-full text-sm">
            <span className="text-gray-500 dark:text-gray-400">Clientes: </span>
            <span className="font-bold text-purple-700 dark:text-purple-400">{overview.active_customers}</span>
          </div>
        </div>
      )}

      {/* Monthly Trends Chart */}
      {trends.length > 0 && (
        <div data-testid="analytics-monthly-trends" className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Tendências Mensais</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => formatCurrency(v)} />
              <Legend />
              <Line type="monotone" dataKey="billed_amount" stroke="#0d9488" name="Cobrado" strokeWidth={2} />
              <Line type="monotone" dataKey="paid_amount" stroke="#16a34a" name="Recebido" strokeWidth={2} />
              <Line type="monotone" dataKey="overdue_amount" stroke="#dc2626" name="Vencido" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Aging Chart */}
      {aging && aging.total_overdue > 0 && (
        <div data-testid="analytics-aging" className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Aging de Cobranças Vencidas ({aging.total_overdue} cobrança(s) — {formatCurrency(aging.total_overdue_amount)})
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={aging.buckets}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => `${v} cobrança(s)`} />
              <Legend />
              <Bar dataKey="count" fill="#f59e0b" name="Cobranças" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Customer Performance Ranking */}
      {customerPerf.length > 0 && (
        <div data-testid="analytics-customer-performance" className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Top Clientes — Performance</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400">Cliente</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400">Cobrado</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400">Pago</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400">Vencido</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400">Status</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400">Sugestão</th>
                </tr>
              </thead>
              <tbody>
                {customerPerf.map((c, i) => {
                  const status = STATUS_LABELS[c.operational_status] || { label: c.operational_status, color: 'text-gray-500' };
                  return (
                    <tr key={i} className="border-b border-gray-100 dark:border-gray-700/50">
                      <td className="py-2 px-2 text-gray-900 dark:text-white font-medium">{c.customer_name}</td>
                      <td className="py-2 px-2 text-right text-gray-700 dark:text-gray-300">{formatCurrency(c.total_billed)}</td>
                      <td className="py-2 px-2 text-right text-green-600">{formatCurrency(c.total_paid)}</td>
                      <td className="py-2 px-2 text-right text-red-600">{formatCurrency(c.total_overdue)}</td>
                      <td className={`py-2 px-2 ${status.color}`}>{status.label}</td>
                      <td className="py-2 px-2 text-gray-500 dark:text-gray-400 text-xs">{ACTION_LABELS[c.suggested_action] || c.suggested_action}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Collection Performance */}
      {collectionPerf && !collectionPerf.insufficient_data && (
        <div data-testid="analytics-collection-performance" className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Performance da Régua de Cobrança</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <p className="text-xs text-gray-500 dark:text-gray-400">Total rascunhos</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{collectionPerf.total_drafts}</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <p className="text-xs text-gray-500 dark:text-gray-400">Clientes contatados</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{collectionPerf.customers_contacted}</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <p className="text-xs text-gray-500 dark:text-gray-400">Rascunhos este mês</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{collectionPerf.followups_this_month}</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <p className="text-xs text-gray-500 dark:text-gray-400">Pagas após follow-up</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{collectionPerf.charges_paid_after_followup}</p>
            </div>
          </div>
          {collectionPerf.estimated_recovered_amount > 0 && (
            <p className="text-sm text-green-600 mt-2">
              💰 Valor recuperado estimado: {formatCurrency(collectionPerf.estimated_recovered_amount)}
            </p>
          )}
        </div>
      )}

      {/* Insights */}
      {insights.length > 0 && (
        <div data-testid="analytics-insights" className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400">Insights</h3>
          </div>
          <ul className="space-y-1.5">
            {insights.map((insight, i) => (
              <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">•</span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* No data message */}
      {overview && overview.total_charges === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Activity className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Você ainda não tem cobranças suficientes para gerar analytics.</p>
          <p className="text-sm mt-1">Crie algumas cobranças para começar a acompanhar sua performance.</p>
        </div>
      )}
    </div>
  );
}
