import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import WhatsAppConnect from '../components/WhatsAppConnect';
import { reportsAPI, billingAPI, chargesAPI } from '../services/api';
import { getErrorMessage } from '../utils/errorHandler';
import Link from 'next/link';
import { TrendingUp, TrendingDown, Wallet, CreditCard, ArrowUpRight, ArrowDownRight, Calendar, Bell, BarChart3, PieChart, Sparkles, Receipt, Link2, Copy, Check, XCircle, Clock, AlertTriangle, DollarSign } from 'lucide-react';

interface DashboardData {
  summary: {
    period: string;
    total_income: number;
    total_expenses: number;
    balance: number;
    transaction_count: number;
    by_category: { category: string; type: string; total: number }[];
  };
  recent_transactions: any[];
  upcoming_reminders: any[];
}

interface Usage {
  plan: string;
  limit: number | string;
  used: number;
  remaining: number | string;
  percentage: number;
}

interface Charge {
  id: number;
  customer_name: string;
  customer_phone?: string;
  amount: number;
  description?: string;
  status: string;
  derived_status?: string;
  payment_link?: string;
  due_date?: string;
  created_at: string;
  paid_at?: string;
}

interface ChargeSummary {
  total_pending: number;
  total_paid: number;
  total_overdue: number;
  count_pending: number;
  count_paid: number;
  count_overdue: number;
  count_cancelled: number;
}

export default function Dashboard() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [charges, setCharges] = useState<Charge[]>([]);
  const [chargeSummary, setChargeSummary] = useState<ChargeSummary | null>(null);
  const [chargeFilter, setChargeFilter] = useState<string>('all');
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashRes, usageRes, chargesRes, summaryRes] = await Promise.all([
        reportsAPI.getDashboard(),
        billingAPI.getUsage(),
        chargesAPI.getAll(50),
        chargesAPI.getSummary(),
      ]);
      setData(dashRes.data);
      setUsage(usageRes.data);
      setCharges(chargesRes.data?.items || []);
      setChargeSummary(summaryRes.data);
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const loadCharges = async (filter: string) => {
    try {
      const statusParam = filter === 'all' ? undefined : filter === 'overdue' ? 'pending' : filter;
      const res = await chargesAPI.getAll(50, statusParam);
      setCharges(res.data?.items || []);
    } catch (err: any) {
      console.error('Error loading charges:', err);
    }
  };

  const handleChargeFilterChange = (filter: string) => {
    setChargeFilter(filter);
    loadCharges(filter);
  };

  const handleCopyLink = async (id: number, link: string) => {
    try {
      await navigator.clipboard.writeText(link);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleCancelCharge = async (id: number) => {
    setCancellingId(id);
    try {
      await chargesAPI.cancel(id);
      await loadCharges(chargeFilter);
      const summaryRes = await chargesAPI.getSummary();
      setChargeSummary(summaryRes.data);
    } catch (err: any) {
      console.error('Error cancelling charge:', err);
    } finally {
      setCancellingId(null);
    }
  };

  const getChargeDisplayStatus = (charge: Charge): string => {
    if (charge.derived_status) return charge.derived_status;
    return charge.status;
  };

  const statusLabelMap: Record<string, string> = {
    pending: 'Pendente',
    paid: 'Pago',
    overdue: 'Vencida',
    cancelled: 'Cancelada',
    expired: 'Expirada',
    failed: 'Falhou',
  };

  const statusColorMap: Record<string, string> = {
    pending: 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30',
    paid: 'text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30',
    overdue: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
    cancelled: 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-900/30',
    expired: 'text-orange-600 dark:text-orange-400 bg-orange-100 dark:bg-orange-900/30',
    failed: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
  };

  const filteredCharges = charges.filter((c) => {
    const displayStatus = getChargeDisplayStatus(c);
    if (chargeFilter === 'all') return true;
    if (chargeFilter === 'overdue') return displayStatus === 'overdue';
    return displayStatus === chargeFilter;
  });

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-500 dark:text-gray-400 text-lg">Carregando seu dashboard...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
            <button
              onClick={() => { setError(''); loadData(); }}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Tentar Novamente
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  const expenseCategories = data?.summary?.by_category?.filter((c) => c.type === 'expense') || [];
  const incomeCategories = data?.summary?.by_category?.filter((c) => c.type === 'income') || [];

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header with gradient */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Dashboard</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {data?.summary?.period || 'Visão geral das suas finanças'}
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
            <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">IA Ativa</span>
          </div>
        </div>

        {/* Summary cards - Modern design */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Income Card */}
          <div className="group relative bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 p-6 border border-green-200 dark:border-green-800 overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-green-400/10 rounded-full -mr-12 -mt-12 group-hover:scale-150 transition-transform duration-500"></div>
            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 bg-green-100 dark:bg-green-900/40 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <ArrowUpRight className="w-4 h-4 text-green-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <p className="text-sm font-medium text-green-700 dark:text-green-300 mb-1">Receitas</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                R$ {Number(data?.summary?.total_income || 0).toFixed(2)}
              </p>
            </div>
          </div>

          {/* Expenses Card */}
          <div className="group relative bg-gradient-to-br from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 p-6 border border-red-200 dark:border-red-800 overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-red-400/10 rounded-full -mr-12 -mt-12 group-hover:scale-150 transition-transform duration-500"></div>
            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/40 rounded-lg">
                  <TrendingDown className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <ArrowDownRight className="w-4 h-4 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <p className="text-sm font-medium text-red-700 dark:text-red-300 mb-1">Despesas</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                R$ {Number(data?.summary?.total_expenses || 0).toFixed(2)}
              </p>
            </div>
          </div>

          {/* Balance Card */}
          <div className={`group relative bg-gradient-to-br ${(data?.summary?.balance || 0) >= 0 ? 'from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800' : 'from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 border-orange-200 dark:border-orange-800'} rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 p-6 border overflow-hidden`}>
            <div className={`absolute top-0 right-0 w-24 h-24 ${(data?.summary?.balance || 0) >= 0 ? 'bg-blue-400/10' : 'bg-orange-400/10'} rounded-full -mr-12 -mt-12 group-hover:scale-150 transition-transform duration-500`}></div>
            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <div className={`p-2 ${(data?.summary?.balance || 0) >= 0 ? 'bg-blue-100 dark:bg-blue-900/40' : 'bg-orange-100 dark:bg-orange-900/40'} rounded-lg`}>
                  <Wallet className={`w-5 h-5 ${(data?.summary?.balance || 0) >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-orange-600 dark:text-orange-400'}`} />
                </div>
              </div>
              <p className={`text-sm font-medium ${(data?.summary?.balance || 0) >= 0 ? 'text-blue-700 dark:text-blue-300' : 'text-orange-700 dark:text-orange-300'} mb-1`}>Saldo Geral</p>
              <p className={`text-2xl font-bold ${(data?.summary?.balance || 0) >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-orange-600 dark:text-orange-400'}`}>
                R$ {Number(data?.summary?.balance || 0).toFixed(2)}
              </p>
            </div>
          </div>

          {/* Transactions Count Card */}
          <div className="group relative bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 p-6 border border-purple-200 dark:border-purple-800 overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-purple-400/10 rounded-full -mr-12 -mt-12 group-hover:scale-150 transition-transform duration-500"></div>
            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 bg-purple-100 dark:bg-purple-900/40 rounded-lg">
                  <CreditCard className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
              <p className="text-sm font-medium text-purple-700 dark:text-purple-300 mb-1">Transações</p>
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {data?.summary?.transaction_count || 0}
              </p>
            </div>
          </div>
        </div>

        {/* Plan usage - Modern card */}
        {usage && (
          <div className="bg-gradient-to-r from-indigo-50 via-purple-50 to-pink-50 dark:from-indigo-900/20 dark:via-purple-900/20 dark:to-pink-900/20 rounded-2xl shadow-lg p-6 border border-indigo-200 dark:border-indigo-800">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-white" />
                </div>
                <div>
                  <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Plano <span className="capitalize bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">{usage.plan}</span>
                  </span>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {usage.used} / {usage.limit === 'unlimited' ? '∞' : usage.limit} transações
                  </p>
                </div>
              </div>
              {usage.limit !== 'unlimited' && usage.percentage >= 80 && (
                <Link href="/plans" className="px-3 py-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-xs font-medium rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all transform hover:scale-105">
                  Upgrade
                </Link>
              )}
            </div>
            {usage.limit !== 'unlimited' ? (
              <div className="relative">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-3 rounded-full transition-all duration-500 ${
                      usage.percentage >= 90 ? 'bg-gradient-to-r from-red-500 to-pink-500' : usage.percentage >= 70 ? 'bg-gradient-to-r from-yellow-500 to-orange-500' : 'bg-gradient-to-r from-indigo-500 to-purple-500'
                    }`}
                    style={{ width: `${Math.min(usage.percentage, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                  {usage.percentage.toFixed(0)}% utilizado
                </p>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <Sparkles className="w-4 h-4" />
                <p className="text-sm font-medium">Transações ilimitadas ativadas!</p>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent transactions - Modern card */}
          <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Transações Recentes</h3>
              </div>
              <Link href="/transactions" className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors flex items-center gap-1">
                Ver todas
                <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="p-6">
              {data?.recent_transactions && data.recent_transactions.length > 0 ? (
                <div className="space-y-3">
                  {data.recent_transactions.map((t: any, i: number) => (
                    <div key={i} className="group flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-all duration-200">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`p-2 rounded-lg ${t.type === 'income' ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                          {t.type === 'income' ? (
                            <TrendingUp className="w-4 h-4 text-green-600 dark:text-green-400" />
                          ) : (
                            <TrendingDown className="w-4 h-4 text-red-600 dark:text-red-400" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {t.category}{t.description ? ` - ${t.description}` : ''}
                          </p>
                          <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                            <Calendar className="w-3 h-3" />
                            {new Date(t.date + 'T00:00:00').toLocaleDateString('pt-BR')}
                          </div>
                        </div>
                      </div>
                      <span className={`text-sm font-bold flex-shrink-0 ml-3 ${t.type === 'income' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        {t.type === 'income' ? '+' : '-'} R$ {Number(t.amount).toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <CreditCard className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">Nenhuma transação registrada</p>
                </div>
              )}
            </div>
          </div>

          {/* Upcoming reminders - Modern card */}
          <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Bell className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Próximos Lembretes</h3>
              </div>
              <Link href="/reminders" className="text-xs font-medium text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors flex items-center gap-1">
                Ver todos
                <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="p-6">
              {data?.upcoming_reminders && data.upcoming_reminders.length > 0 ? (
                <div className="space-y-3">
                  {data.upcoming_reminders.map((r: any, i: number) => (
                    <div key={i} className="group flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-all duration-200">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                          <Bell className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        </div>
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{r.title}</span>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 flex-shrink-0 ml-3">
                        <Calendar className="w-3 h-3" />
                        {new Date(r.due_date).toLocaleDateString('pt-BR')}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Bell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum lembrete pendente</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Categories breakdown - Modern card */}
        {expenseCategories.length > 0 && (
          <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-2 mb-6">
              <PieChart className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Despesas por Categoria</h3>
            </div>
            <div className="space-y-4">
              {expenseCategories.map((cat, i) => {
                const maxTotal = Math.max(...expenseCategories.map((c) => c.total));
                const pct = maxTotal > 0 ? (cat.total / maxTotal) * 100 : 0;
                const colors = [
                  'from-red-500 to-pink-500',
                  'from-orange-500 to-amber-500',
                  'from-yellow-500 to-orange-500',
                  'from-purple-500 to-pink-500',
                  'from-blue-500 to-indigo-500'
                ];
                const colorClass = colors[i % colors.length];
                return (
                  <div key={i} className="group">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">{cat.category}</span>
                      <span className="text-sm font-bold text-gray-900 dark:text-gray-100">R$ {Number(cat.total).toFixed(2)}</span>
                    </div>
                    <div className="relative w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                      <div 
                        className={`h-3 rounded-full bg-gradient-to-r ${colorClass} transition-all duration-500 group-hover:scale-x-105 origin-left`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{pct.toFixed(0)}% do total</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Charge Summary Cards */}
        {chargeSummary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-gradient-to-br from-yellow-50 to-amber-50 dark:from-yellow-900/20 dark:to-amber-900/20 rounded-2xl shadow-lg p-5 border border-yellow-200 dark:border-yellow-800">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                <span className="text-xs font-medium text-yellow-700 dark:text-yellow-300">A Receber</span>
              </div>
              <p className="text-xl font-bold text-yellow-600 dark:text-yellow-400">R$ {Number(chargeSummary.total_pending + chargeSummary.total_overdue).toFixed(2)}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{chargeSummary.count_pending + chargeSummary.count_overdue} cobrança(s)</p>
            </div>
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 rounded-2xl shadow-lg p-5 border border-emerald-200 dark:border-emerald-800">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-medium text-emerald-700 dark:text-emerald-300">Recebido</span>
              </div>
              <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">R$ {Number(chargeSummary.total_paid).toFixed(2)}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{chargeSummary.count_paid} cobrança(s)</p>
            </div>
            <div className="bg-gradient-to-br from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 rounded-2xl shadow-lg p-5 border border-yellow-200 dark:border-yellow-800">
              <div className="flex items-center gap-2 mb-2">
                <Receipt className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                <span className="text-xs font-medium text-yellow-700 dark:text-yellow-300">Pendentes</span>
              </div>
              <p className="text-xl font-bold text-yellow-600 dark:text-yellow-400">{chargeSummary.count_pending - chargeSummary.count_overdue}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">aguardando pagamento</p>
            </div>
            <div className="bg-gradient-to-br from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 rounded-2xl shadow-lg p-5 border border-red-200 dark:border-red-800">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
                <span className="text-xs font-medium text-red-700 dark:text-red-300">Vencidas</span>
              </div>
              <p className="text-xl font-bold text-red-600 dark:text-red-400">{chargeSummary.count_overdue}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">precisam de atenção</p>
            </div>
          </div>
        )}

        {/* Charges - Enhanced section */}
        <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <Receipt className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Cobranças</h3>
            </div>
            <div className="flex items-center gap-1 flex-wrap">
              {['all', 'pending', 'paid', 'overdue', 'cancelled'].map((f) => (
                <button
                  key={f}
                  onClick={() => handleChargeFilterChange(f)}
                  className={`px-3 py-1 text-xs font-medium rounded-lg transition-all ${
                    chargeFilter === f
                      ? 'bg-emerald-600 text-white shadow-md'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {f === 'all' ? 'Todas' : f === 'pending' ? 'Pendentes' : f === 'paid' ? 'Pagas' : f === 'overdue' ? 'Vencidas' : 'Canceladas'}
                </button>
              ))}
            </div>
          </div>
          <div className="p-6">
            {filteredCharges.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Cliente</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Valor</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 hidden sm:table-cell">Descrição</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Status</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 hidden md:table-cell">Vencimento</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 hidden lg:table-cell">Criada</th>
                      <th className="text-center py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCharges.map((c) => {
                      const displayStatus = getChargeDisplayStatus(c);
                      const statusLabel = statusLabelMap[displayStatus] || displayStatus;
                      const statusColor = statusColorMap[displayStatus] || statusColorMap['pending'];
                      const canCancel = displayStatus === 'pending' || displayStatus === 'overdue';
                      return (
                        <tr key={c.id} className="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                          <td className="py-3 px-3">
                            <p className="font-medium text-gray-900 dark:text-gray-100">{c.customer_name}</p>
                            {c.customer_phone && <p className="text-xs text-gray-400 dark:text-gray-500">{c.customer_phone}</p>}
                          </td>
                          <td className="py-3 px-3 text-right font-bold text-gray-900 dark:text-gray-100">R$ {Number(c.amount).toFixed(2)}</td>
                          <td className="py-3 px-3 hidden sm:table-cell text-gray-600 dark:text-gray-400 max-w-xs truncate">{c.description || '-'}</td>
                          <td className="py-3 px-3">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusColor}`}>
                              {statusLabel}
                            </span>
                          </td>
                          <td className="py-3 px-3 hidden md:table-cell text-gray-500 dark:text-gray-400 text-xs">{c.due_date ? new Date(c.due_date + 'T00:00:00').toLocaleDateString('pt-BR') : '-'}</td>
                          <td className="py-3 px-3 hidden lg:table-cell text-gray-500 dark:text-gray-400 text-xs">{new Date(c.created_at).toLocaleDateString('pt-BR')}</td>
                          <td className="py-3 px-3">
                            <div className="flex items-center justify-center gap-1">
                              {c.payment_link && (
                                <>
                                  <a href={c.payment_link} target="_blank" rel="noopener noreferrer" className="p-1.5 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-lg transition-colors" title="Abrir link">
                                    <Link2 className="w-4 h-4" />
                                  </a>
                                  <button
                                    onClick={() => handleCopyLink(c.id, c.payment_link!)}
                                    className="p-1.5 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                                    title="Copiar link"
                                  >
                                    {copiedId === c.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                  </button>
                                </>
                              )}
                              {canCancel && (
                                <button
                                  onClick={() => handleCancelCharge(c.id)}
                                  disabled={cancellingId === c.id}
                                  className="p-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
                                  title="Cancelar cobrança"
                                >
                                  {cancellingId === c.id ? (
                                    <div className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                                  ) : (
                                    <XCircle className="w-4 h-4" />
                                  )}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8">
                <Receipt className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">Nenhuma cobrança encontrada</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Use o WhatsApp para criar cobranças</p>
              </div>
            )}
          </div>
        </div>

        {/* WhatsApp Connection */}
        <WhatsAppConnect />
      </div>
    </Layout>
  );
}
