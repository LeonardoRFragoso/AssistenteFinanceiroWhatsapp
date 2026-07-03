import { useState, useEffect, useCallback } from "react";
import {
  FileText,
  RefreshCw,
  AlertCircle,
  Calendar,
  CheckCircle,
  Bell,
  XCircle,
  Receipt,
  TrendingUp,
} from "lucide-react";

interface DetectedBill {
  id: number;
  title: string;
  beneficiary_name: string;
  amount: string;
  currency: string;
  due_date: string;
  category: string | null;
  status: string;
  risk_level: string;
  is_demo_data: boolean;
  bill_type: string;
}

interface BillSummary {
  overdue_total: string;
  due_today_total: string;
  upcoming_7_days_total: string;
  upcoming_30_days_total: string;
  open_total: string;
  overdue_count: number;
  due_today_count: number;
  upcoming_7_days_count: number;
  upcoming_30_days_count: number;
  open_count: number;
  top_categories: Array<{ category: string; total: string }>;
  top_beneficiaries: Array<{ beneficiary: string; total: string }>;
  largest_bill: { id: number; title: string; amount: string; due_date: string; beneficiary: string } | null;
  is_demo_data: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  detected: "Detectada",
  pending: "Pendente",
  due_today: "Vence Hoje",
  overdue: "Vencida",
  paid_manual: "Paga (Manual)",
  ignored: "Ignorada",
  cancelled: "Cancelada",
  expired: "Expirada",
};

const STATUS_COLORS: Record<string, string> = {
  detected: "bg-blue-100 text-blue-800",
  pending: "bg-yellow-100 text-yellow-800",
  due_today: "bg-orange-100 text-orange-800",
  overdue: "bg-red-100 text-red-800",
  paid_manual: "bg-green-100 text-green-800",
  ignored: "bg-gray-100 text-gray-800",
  cancelled: "bg-gray-100 text-gray-800",
  expired: "bg-gray-100 text-gray-800",
};

export default function BillsSection() {
  const [bills, setBills] = useState<DetectedBill[]>([]);
  const [summary, setSummary] = useState<BillSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");

  const fetchBills = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      if (search) params.append("search", search);
      const res = await fetch(`/api/bills?${params}`);
      if (res.ok) {
        const data = await res.json();
        setBills(data);
      }
    } catch {
      // ignore
    }
  }, [statusFilter, search]);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`/api/bills/summary`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    Promise.all([fetchBills(), fetchSummary()]).finally(() => setLoading(false));
  }, [fetchBills, fetchSummary]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await fetch(`/api/bills/sync/fake`, { method: "POST" });
      await Promise.all([fetchBills(), fetchSummary()]);
    } catch {
      // ignore
    } finally {
      setSyncing(false);
    }
  };

  const handleAction = async (billId: number, action: string) => {
    try {
      await fetch(`/api/bills/${billId}/${action}`, { method: "POST" });
      await Promise.all([fetchBills(), fetchSummary()]);
    } catch {
      // ignore
    }
  };

  const handleFakePaymentIntent = async (billId: number) => {
    try {
      await fetch(`/api/bills/${billId}/payment-intents/fake`, { method: "POST" });
      await fetchBills();
    } catch {
      // ignore
    }
  };

  const formatCurrency = (value: string) => {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(parseFloat(value));
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("pt-BR");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div data-testid="bills-section" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-indigo-600" />
          <h2 className="text-xl font-bold text-gray-900">Contas a Pagar</h2>
          <span className="rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-800">
            Demo/Fake
          </span>
        </div>
        <button
          data-testid="sync-fake-bills-button"
          onClick={handleSync}
          disabled={syncing}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
          Sincronizar dados demo
        </button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <span className="text-sm font-medium text-red-900">Vencidas</span>
            </div>
            <p className="mt-2 text-2xl font-bold text-red-900">{formatCurrency(summary.overdue_total)}</p>
            <p className="text-xs text-red-700">{summary.overdue_count} contas</p>
          </div>
          <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-orange-600" />
              <span className="text-sm font-medium text-orange-900">Vencem hoje</span>
            </div>
            <p className="mt-2 text-2xl font-bold text-orange-900">{formatCurrency(summary.due_today_total)}</p>
            <p className="text-xs text-orange-700">{summary.due_today_count} contas</p>
          </div>
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-blue-600" />
              <span className="text-sm font-medium text-blue-900">Próximos 7 dias</span>
            </div>
            <p className="mt-2 text-2xl font-bold text-blue-900">{formatCurrency(summary.upcoming_7_days_total)}</p>
            <p className="text-xs text-blue-700">{summary.upcoming_7_days_count} contas</p>
          </div>
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-indigo-600" />
              <span className="text-sm font-medium text-indigo-900">Total em aberto</span>
            </div>
            <p className="mt-2 text-2xl font-bold text-indigo-900">{formatCurrency(summary.open_total)}</p>
            <p className="text-xs text-indigo-700">{summary.open_count} contas</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">Todos os status</option>
          <option value="pending">Pendente</option>
          <option value="due_today">Vence hoje</option>
          <option value="overdue">Vencida</option>
          <option value="paid_manual">Paga (manual)</option>
          <option value="ignored">Ignorada</option>
        </select>
        <input
          type="text"
          placeholder="Buscar por beneficiário..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
      </div>

      {/* Bills list */}
      <div className="overflow-hidden rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Conta</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Beneficiário</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Vencimento</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Valor</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {bills.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  Nenhuma conta encontrada. Clique em "Sincronizar dados demo" para gerar contas de demonstração.
                </td>
              </tr>
            ) : (
              bills.map((bill) => (
                <tr key={bill.id} data-testid={`bill-row-${bill.id}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Receipt className="h-4 w-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">{bill.title}</span>
                      {bill.is_demo_data && (
                        <span data-testid={`bill-demo-badge-${bill.id}`} className="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800">
                          Demo
                        </span>
                      )}
                    </div>
                    {bill.category && <p className="text-xs text-gray-500">{bill.category}</p>}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">{bill.beneficiary_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{formatDate(bill.due_date)}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{formatCurrency(bill.amount)}</td>
                  <td className="px-4 py-3">
                    <span data-testid={`bill-status-${bill.id}`} className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${STATUS_COLORS[bill.status] || "bg-gray-100 text-gray-800"}`}>
                      {STATUS_LABELS[bill.status] || bill.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        data-testid={`bill-reminder-button-${bill.id}`}
                        onClick={() => handleAction(bill.id, "reminders")}
                        title="Criar lembrete"
                        className="rounded p-1.5 text-blue-600 hover:bg-blue-50"
                      >
                        <Bell className="h-4 w-4" />
                      </button>
                      <button
                        data-testid={`bill-mark-paid-button-${bill.id}`}
                        onClick={() => handleAction(bill.id, "mark-paid-manual")}
                        title="Marcar como paga (manual)"
                        className="rounded p-1.5 text-green-600 hover:bg-green-50"
                      >
                        <CheckCircle className="h-4 w-4" />
                      </button>
                      <button
                        data-testid={`bill-ignore-button-${bill.id}`}
                        onClick={() => handleAction(bill.id, "ignore")}
                        title="Ignorar"
                        className="rounded p-1.5 text-gray-600 hover:bg-gray-100"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                      <button
                        data-testid={`bill-fake-payment-intent-button-${bill.id}`}
                        onClick={() => handleFakePaymentIntent(bill.id)}
                        title="Preparar intenção fake"
                        className="rounded p-1.5 text-purple-600 hover:bg-purple-50"
                      >
                        <Receipt className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-500">
        ⚠️ Todos os dados são de demonstração. Nenhum pagamento real é executado.
      </p>
    </div>
  );
}
