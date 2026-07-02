import { useEffect, useState } from 'react';
import { customersAPI, messageTemplatesAPI, collectionAPI } from '../services/api';
import { getErrorMessage } from '../utils/errorHandler';
import { Users, MessageSquare, Calendar, AlertTriangle, CheckCircle, XCircle, Eye, FileText, Bell, Clock } from 'lucide-react';

interface Customer {
  id: number;
  name: string;
  phone?: string;
  email?: string;
  operational_status?: string;
  total_charges_count?: number;
  total_paid_amount?: number;
  total_pending_amount?: number;
  total_overdue_amount?: number;
  has_overdue?: boolean;
}

interface MessageTemplate {
  id: number;
  name: string;
  tone: string;
  template_text: string;
  active: boolean;
}

interface CollectionRule {
  id: number;
  name: string;
  days_offset: number;
  trigger_type: string;
  active: boolean;
}

interface FollowupItem {
  charge_id: number;
  customer_name: string;
  amount: number;
  due_date?: string;
  days_overdue: number;
  rendered_message: string;
  template_name?: string;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  good_payer: { label: 'Bom pagador', color: 'text-green-600' },
  late_payer: { label: 'Pagamento em atraso', color: 'text-yellow-600' },
  frequent_late: { label: 'Atrasa frequentemente', color: 'text-red-600' },
  new_customer: { label: 'Novo cliente', color: 'text-blue-600' },
  inactive_customer: { label: 'Inativo', color: 'text-gray-500' },
};

const TONE_LABELS: Record<string, string> = {
  friendly: 'Amigável',
  neutral: 'Neutro',
  firm: 'Firme',
};

export default function CustomerIntelligenceSection() {
  const [activeTab, setActiveTab] = useState<'customers' | 'templates' | 'collection'>('customers');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerSearch, setCustomerSearch] = useState('');
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [rules, setRules] = useState<CollectionRule[]>([]);
  const [followups, setFollowups] = useState<FollowupItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [previewTemplateId, setPreviewTemplateId] = useState<number | null>(null);
  const [previewText, setPreviewText] = useState('');

  useEffect(() => {
    if (activeTab === 'customers') loadCustomers();
    else if (activeTab === 'templates') loadTemplates();
    else if (activeTab === 'collection') loadCollection();
  }, [activeTab]);

  const loadCustomers = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await customersAPI.list({ search: customerSearch || undefined, page: 1, page_size: 50 });
      setCustomers(res.data.items || []);
    } catch (e) {
      setError(getErrorMessage(e));
    }
    setLoading(false);
  };

  const loadTemplates = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await messageTemplatesAPI.list();
      setTemplates(res.data.items || []);
    } catch (e) {
      setError(getErrorMessage(e));
    }
    setLoading(false);
  };

  const loadCollection = async () => {
    setLoading(true);
    setError('');
    try {
      const [rulesRes, followupsRes] = await Promise.all([
        collectionAPI.listRules(),
        collectionAPI.getOverdueFollowups(10),
      ]);
      setRules(rulesRes.data.items || []);
      setFollowups(followupsRes.data.items || []);
    } catch (e) {
      setError(getErrorMessage(e));
    }
    setLoading(false);
  };

  const handlePreviewTemplate = async (id: number) => {
    try {
      const res = await messageTemplatesAPI.preview(id, {});
      setPreviewText(res.data.rendered_text);
      setPreviewTemplateId(id);
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleDeactivateTemplate = async (id: number) => {
    try {
      await messageTemplatesAPI.deactivate(id);
      loadTemplates();
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleDeactivateRule = async (id: number) => {
    try {
      await collectionAPI.deactivateRule(id);
      loadCollection();
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const maskPhone = (phone?: string) => {
    if (!phone) return '-';
    if (phone.length <= 4) return phone;
    return phone.slice(0, -4) + '****';
  };

  const totalCustomers = customers.length;
  const overdueCustomers = customers.filter(c => c.has_overdue).length;
  const goodPayers = customers.filter(c => c.operational_status === 'good_payer').length;

  return (
    <div className="mt-8 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Users className="w-5 h-5 text-teal-600" />
          Customer Intelligence & Régua de Cobrança
        </h2>
      </div>

      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('customers')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'customers'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
          }`}
        >
          <Users className="w-4 h-4 inline mr-1" /> Clientes
        </button>
        <button
          onClick={() => setActiveTab('templates')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'templates'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
          }`}
        >
          <MessageSquare className="w-4 h-4 inline mr-1" /> Templates
        </button>
        <button
          onClick={() => setActiveTab('collection')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'collection'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
          }`}
        >
          <Calendar className="w-4 h-4 inline mr-1" /> Régua de Cobrança
        </button>
      </div>

      <div className="p-6">
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">Carregando...</div>
        )}

        {!loading && activeTab === 'customers' && (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-teal-50 dark:bg-teal-900/20 rounded-lg p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">Total de clientes</div>
                <div className="text-2xl font-bold text-teal-600">{totalCustomers}</div>
              </div>
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">Com vencidas</div>
                <div className="text-2xl font-bold text-red-600">{overdueCustomers}</div>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">Bons pagadores</div>
                <div className="text-2xl font-bold text-green-600">{goodPayers}</div>
              </div>
            </div>

            <div className="flex gap-2 mb-4">
              <input
                type="text"
                placeholder="Buscar por nome ou telefone..."
                value={customerSearch}
                onChange={(e) => setCustomerSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadCustomers()}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
              <button
                onClick={loadCustomers}
                className="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm hover:bg-teal-700 transition-colors"
              >
                Buscar
              </button>
            </div>

            {customers.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                Nenhum cliente encontrado. Crie cobranças para que clientes sejam cadastrados automaticamente.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-left py-2 px-3 font-medium text-gray-600 dark:text-gray-400">Nome</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-600 dark:text-gray-400">Telefone</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-600 dark:text-gray-400">Total pago</th>
                      <th className="text-right py-2 px-3 font-medium text-gray-600 dark:text-gray-400">Vencido</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-600 dark:text-gray-400">Status</th>
                      <th className="text-center py-2 px-3 font-medium text-gray-600 dark:text-gray-400">Ação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customers.map((c) => {
                      const status = STATUS_LABELS[c.operational_status || ''] || { label: c.operational_status || '-', color: 'text-gray-500' };
                      return (
                        <tr key={c.id} className="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="py-2 px-3 text-gray-900 dark:text-white">{c.name}</td>
                          <td className="py-2 px-3 text-gray-500 dark:text-gray-400">{maskPhone(c.phone)}</td>
                          <td className="py-2 px-3 text-right text-gray-900 dark:text-white">R$ {(c.total_paid_amount || 0).toFixed(2)}</td>
                          <td className="py-2 px-3 text-right">
                            {c.has_overdue ? (
                              <span className="text-red-600 font-medium">R$ {(c.total_overdue_amount || 0).toFixed(2)}</span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                          <td className="py-2 px-3">
                            <span className={status.color}>{status.label}</span>
                          </td>
                          <td className="py-2 px-3 text-center">
                            <button
                              onClick={() => setSelectedCustomer(c)}
                              className="text-teal-600 hover:text-teal-700"
                              title="Ver histórico"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {selectedCustomer && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedCustomer(null)}>
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg max-w-lg w-full p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white">{selectedCustomer.name}</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">{maskPhone(selectedCustomer.phone)}</p>
                    </div>
                    <button onClick={() => setSelectedCustomer(null)} className="text-gray-400 hover:text-gray-600">
                      <XCircle className="w-5 h-5" />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                      <div className="text-gray-500 dark:text-gray-400">Total cobranças</div>
                      <div className="font-bold text-gray-900 dark:text-white">{selectedCustomer.total_charges_count || 0}</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                      <div className="text-gray-500 dark:text-gray-400">Status</div>
                      <div className="font-bold">
                        <span className={STATUS_LABELS[selectedCustomer.operational_status || '']?.color || 'text-gray-500'}>
                          {STATUS_LABELS[selectedCustomer.operational_status || '']?.label || '-'}
                        </span>
                      </div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                      <div className="text-gray-500 dark:text-gray-400">Total pago</div>
                      <div className="font-bold text-green-600">R$ {(selectedCustomer.total_paid_amount || 0).toFixed(2)}</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                      <div className="text-gray-500 dark:text-gray-400">Total vencido</div>
                      <div className="font-bold text-red-600">R$ {(selectedCustomer.total_overdue_amount || 0).toFixed(2)}</div>
                    </div>
                  </div>
                  {selectedCustomer.has_overdue && (
                    <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 rounded-lg text-sm">
                      <AlertTriangle className="w-4 h-4 inline mr-1" />
                      Este cliente tem cobranças vencidas. Use a régua de cobrança para gerar mensagens.
                    </div>
                  )}
                  <p className="mt-4 text-xs text-gray-400">
                    Score operacional de relacionamento — não é score de crédito.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {!loading && activeTab === 'templates' && (
          <div>
            {templates.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                Nenhum template encontrado. Crie templates via API ou WhatsApp.
              </div>
            ) : (
              <div className="space-y-3">
                {templates.map((t) => (
                  <div key={t.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <span className="font-medium text-gray-900 dark:text-white">{t.name}</span>
                        <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                          t.tone === 'friendly' ? 'bg-green-100 text-green-700' :
                          t.tone === 'firm' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {TONE_LABELS[t.tone] || t.tone}
                        </span>
                        {!t.active && <span className="ml-2 text-xs text-gray-400">(inativo)</span>}
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handlePreviewTemplate(t.id)}
                          className="text-xs px-3 py-1 bg-teal-50 dark:bg-teal-900/20 text-teal-600 rounded hover:bg-teal-100"
                        >
                          Prévia
                        </button>
                        {t.active && (
                          <button
                            onClick={() => handleDeactivateTemplate(t.id)}
                            className="text-xs px-3 py-1 bg-red-50 dark:bg-red-900/20 text-red-600 rounded hover:bg-red-100"
                          >
                            Desativar
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap line-clamp-3">{t.template_text}</p>
                    {previewTemplateId === t.id && previewText && (
                      <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap border border-gray-200 dark:border-gray-600">
                        <div className="text-xs text-gray-400 mb-1">Prévia renderizada:</div>
                        {previewText}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!loading && activeTab === 'collection' && (
          <div>
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-1">
                <AlertTriangle className="w-4 h-4 text-red-500" /> Cobranças vencidas ({followups.length})
              </h3>
              {followups.length === 0 ? (
                <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                  Nenhuma cobrança vencida. Tudo em dia!
                </div>
              ) : (
                <div className="space-y-2">
                  {followups.map((f) => (
                    <div key={f.charge_id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-medium text-gray-900 dark:text-white">{f.customer_name}</span>
                          <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                            R$ {f.amount.toFixed(2)} — venceu há {f.days_overdue} dia(s)
                          </span>
                        </div>
                      </div>
                      <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-700/50 rounded text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap max-h-24 overflow-y-auto">
                        {f.rendered_message}
                      </div>
                      <div className="mt-2 text-xs text-yellow-600 dark:text-yellow-400">
                        <Bell className="w-3 h-3 inline mr-1" />
                        Rascunho apenas — nenhum envio automático. Confirmação explícita necessária.
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-1">
                <Calendar className="w-4 h-4 text-teal-500" /> Regras de cobrança ({rules.length})
              </h3>
              {rules.length === 0 ? (
                <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">
                  Nenhuma regra configurada. Use o WhatsApp para criar: "crie uma régua para lembrar 2 dias antes do vencimento"
                </div>
              ) : (
                <div className="space-y-2">
                  {rules.map((r) => (
                    <div key={r.id} className="flex justify-between items-center border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <div>
                        <span className="font-medium text-gray-900 dark:text-white text-sm">{r.name}</span>
                        <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                          {r.trigger_type === 'before_due' ? `${r.days_offset} dia(s) antes` :
                           r.trigger_type === 'after_due' ? `${r.days_offset} dia(s) após` :
                           'no vencimento'}
                        </span>
                      </div>
                      <button
                        onClick={() => handleDeactivateRule(r.id)}
                        className="text-xs px-3 py-1 bg-red-50 dark:bg-red-900/20 text-red-600 rounded hover:bg-red-100"
                      >
                        Desativar
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg text-xs">
              <Clock className="w-4 h-4 inline mr-1" />
              As regras de cobrança não enviam mensagens automaticamente. Elas apenas preparam rascunhos para confirmação explícita do usuário.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
