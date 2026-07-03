import { useState, useEffect, useCallback } from "react";
import {
  Wallet,
  RefreshCw,
  BarChart3,
  AlertTriangle,
} from "lucide-react";

interface ConnectedAccount {
  id: number;
  institution_name: string;
  account_number_masked: string;
  account_type: string;
  balance_available: string;
  balance_current: string;
  currency: string;
  is_demo_data: boolean;
  status: string;
}

interface BankTransaction {
  id: number;
  transaction_type: string;
  amount: string;
  description: string;
  merchant_name: string | null;
  category: string | null;
  transaction_date: string | null;
  is_demo_data: boolean;
}

interface OpenFinanceStatus {
  enabled: boolean;
  provider: string;
  real_provider_configured: boolean;
  demo_mode: boolean;
  real_data_access: boolean;
  message: string;
}

export default function OpenFinanceSection({
  token,
  organizationId,
}: {
  token: string;
  organizationId: number | null;
}) {
  const [status, setStatus] = useState<OpenFinanceStatus | null>(null);
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasConsent, setHasConsent] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/open-finance/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // Status fetch is non-critical
    }
  }, [token, API_BASE]);

  const fetchAccounts = useCallback(async () => {
    if (!organizationId) return;
    try {
      const res = await fetch(`${API_BASE}/open-finance/accounts`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-ID": String(organizationId),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setAccounts(data);
      } else if (res.status === 403) {
        setError("Você não tem permissão para acessar Open Finance.");
      }
    } catch {
      setError("Erro ao buscar contas conectadas.");
    }
  }, [token, organizationId, API_BASE]);

  const fetchTransactions = useCallback(async () => {
    if (!organizationId) return;
    try {
      const res = await fetch(
        `${API_BASE}/open-finance/transactions?limit=10`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Organization-ID": String(organizationId),
          },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setTransactions(data);
      }
    } catch {
      // Non-critical
    }
  }, [token, organizationId, API_BASE]);

  const fetchConsents = useCallback(async () => {
    if (!organizationId) return;
    try {
      const res = await fetch(`${API_BASE}/open-finance/consents`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-ID": String(organizationId),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setHasConsent(data.length > 0);
      }
    } catch {
      // Non-critical
    }
  }, [token, organizationId, API_BASE]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (organizationId) {
      setLoading(true);
      Promise.all([fetchAccounts(), fetchTransactions(), fetchConsents()]).finally(() => {
        setLoading(false);
      });
    }
  }, [organizationId, fetchAccounts, fetchTransactions, fetchConsents]);

  const handleCreateConsent = async () => {
    if (!organizationId) return;
    setSyncing(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/open-finance/consents/fake`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-ID": String(organizationId),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ institution_id: "fake_bank" }),
      });
      if (res.ok) {
        setHasConsent(true);
        await handleSync();
      } else if (res.status === 403) {
        setError("Você não tem permissão para criar consentimentos.");
      } else {
        setError("Erro ao criar consentimento.");
      }
    } catch {
      setError("Erro de conexão ao criar consentimento.");
    } finally {
      setSyncing(false);
    }
  };

  const handleSync = async () => {
    if (!organizationId) return;
    setSyncing(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/open-finance/sync/fake`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-ID": String(organizationId),
        },
      });
      if (res.ok) {
        await Promise.all([fetchAccounts(), fetchTransactions()]);
      } else if (res.status === 403) {
        setError("Você não tem permissão para sincronizar dados.");
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Erro ao sincronizar dados.");
      }
    } catch {
      setError("Erro de conexão ao sincronizar.");
    } finally {
      setSyncing(false);
    }
  };

  const formatCurrency = (value: string, currency: string = "BRL") => {
    const num = parseFloat(value);
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency,
    }).format(num);
  };

  const totalAvailable = accounts.reduce(
    (sum, a) => sum + parseFloat(a.balance_available || "0"),
    0
  );

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6" data-testid="open-finance-section">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Wallet className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Open Finance
          </h2>
        </div>
        {status?.demo_mode && (
          <span className="px-3 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
            Demo
          </span>
        )}
      </div>

      {/* Demo warning */}
      {status?.demo_mode && (
        <div className="mb-4 p-3 rounded-md bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              {status.message} Todos os dados exibidos são fictícios para demonstração.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 rounded-md bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 mb-6">
        {!hasConsent && (
          <button
            onClick={handleCreateConsent}
            disabled={syncing}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
            data-testid="of-create-consent-btn"
          >
            {syncing ? "Criando..." : "Criar consentimento demo"}
          </button>
        )}
        {hasConsent && (
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
            data-testid="of-sync-btn"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Sincronizando..." : "Sincronizar dados demo"}
          </button>
        )}
      </div>

      {/* Balance summary */}
      {accounts.length > 0 && (
        <div className="mb-6 p-4 rounded-md bg-indigo-50 dark:bg-indigo-900/20" data-testid="of-balance-summary">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Saldo total disponível</p>
          <p className="text-2xl font-bold text-indigo-700 dark:text-indigo-300">
            {formatCurrency(totalAvailable.toString())}
          </p>
        </div>
      )}

      {/* Connected accounts */}
      {accounts.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Contas conectadas
          </h3>
          <div className="space-y-2">
            {accounts.map((acc) => (
              <div
                key={acc.id}
                className="flex items-center justify-between p-3 rounded-md border border-gray-200 dark:border-gray-700"
                data-testid={`of-account-${acc.id}`}
              >
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {acc.institution_name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {acc.account_type} — {acc.account_number_masked}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">
                    {formatCurrency(acc.balance_available, acc.currency)}
                  </p>
                  {acc.is_demo_data && (
                    <span className="text-xs text-yellow-600 dark:text-yellow-400">demo</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent transactions */}
      {transactions.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Transações recentes
          </h3>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {transactions.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700/50"
                data-testid={`of-tx-${tx.id}`}
              >
                <div className="flex items-center gap-2">
                  <span className={tx.transaction_type === "credit" ? "text-green-600" : "text-red-600"}>
                    {tx.transaction_type === "credit" ? "➕" : "➖"}
                  </span>
                  <div>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {tx.description}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {tx.merchant_name} — {tx.category}
                    </p>
                  </div>
                </div>
                <span className={`text-sm font-medium ${tx.transaction_type === "credit" ? "text-green-600" : "text-red-600"}`}>
                  {formatCurrency(Math.abs(parseFloat(tx.amount)).toString())}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && accounts.length === 0 && !error && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p className="text-sm">
            Nenhuma conta conectada. Crie um consentimento demo para começar.
          </p>
        </div>
      )}
    </div>
  );
}
