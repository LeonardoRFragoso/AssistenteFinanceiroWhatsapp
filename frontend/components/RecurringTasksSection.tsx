import { useEffect, useState } from 'react';
import { recurringTasksAPI } from '../services/api';
import { getErrorMessage } from '../utils/errorHandler';
import { Repeat, Plus, X, Trash2, Clock } from 'lucide-react';

interface RecurringTask {
  id: number;
  title: string;
  description?: string;
  recurrence_type: string;
  day_of_week?: number;
  day_of_month?: number;
  next_run_at: string;
  active: boolean;
  created_at: string;
}

const RECURRENCE_LABELS: Record<string, string> = {
  daily: 'Diária',
  weekly: 'Semanal',
  monthly: 'Mensal',
};

const WEEKDAY_LABELS = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];

export default function RecurringTasksSection() {
  const [tasks, setTasks] = useState<RecurringTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    recurrence_type: 'daily',
    day_of_week: '1',
    day_of_month: '1',
  });

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      setLoading(true);
      const res = await recurringTasksAPI.list();
      setTasks(res.data.items || []);
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      const data: any = {
        title: formData.title,
        recurrence_type: formData.recurrence_type,
      };
      if (formData.description) data.description = formData.description;
      if (formData.recurrence_type === 'weekly') data.day_of_week = parseInt(formData.day_of_week);
      if (formData.recurrence_type === 'monthly') data.day_of_month = parseInt(formData.day_of_month);

      await recurringTasksAPI.create(data);
      setShowForm(false);
      setFormData({ title: '', description: '', recurrence_type: 'daily', day_of_week: '1', day_of_month: '1' });
      await loadTasks();
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  const handleCancel = async (id: number) => {
    setCancellingId(id);
    try {
      await recurringTasksAPI.cancel(id);
      await loadTasks();
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setCancellingId(null);
    }
  };

  const activeTasks = tasks.filter(t => t.active);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Repeat className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Tarefas Recorrentes</h2>
          {activeTasks.length > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full">
              {activeTasks.length} ativa(s)
            </span>
          )}
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg transition-colors"
        >
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? 'Cancelar' : 'Nova tarefa'}
        </button>
      </div>

      {error && (
        <div className="mb-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="mb-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Título</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
              maxLength={255}
              placeholder="Ex: Cobrar o João sobre a fatura"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Descrição (opcional)</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              maxLength={1000}
              placeholder="Ex: Lembrar de enviar o link de pagamento"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Recorrência</label>
            <select
              value={formData.recurrence_type}
              onChange={(e) => setFormData({ ...formData, recurrence_type: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
            >
              <option value="daily">Diária</option>
              <option value="weekly">Semanal</option>
              <option value="monthly">Mensal</option>
            </select>
          </div>
          {formData.recurrence_type === 'weekly' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Dia da semana</label>
              <select
                value={formData.day_of_week}
                onChange={(e) => setFormData({ ...formData, day_of_week: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              >
                {WEEKDAY_LABELS.map((day, i) => (
                  <option key={i} value={i}>{day}</option>
                ))}
              </select>
            </div>
          )}
          {formData.recurrence_type === 'monthly' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Dia do mês</label>
              <input
                type="number"
                min={1}
                max={31}
                value={formData.day_of_month}
                onChange={(e) => setFormData({ ...formData, day_of_month: e.target.value })}
                required
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              />
            </div>
          )}
          <button
            type="submit"
            disabled={creating}
            className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            {creating ? 'Criando...' : 'Criar tarefa recorrente'}
          </button>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="w-6 h-6 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : activeTasks.length === 0 ? (
        <div className="text-center py-8">
          <Repeat className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Nenhuma tarefa recorrente ativa</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Crie uma tarefa para receber lembretes automáticos</p>
        </div>
      ) : (
        <div className="space-y-2">
          {activeTasks.map((task) => (
            <div
              key={task.id}
              className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{task.title}</p>
                  <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full whitespace-nowrap">
                    {RECURRENCE_LABELS[task.recurrence_type] || task.recurrence_type}
                  </span>
                </div>
                {task.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">{task.description}</p>
                )}
                <div className="flex items-center gap-1 mt-1">
                  <Clock className="w-3 h-3 text-gray-400" />
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    Próxima: {new Date(task.next_run_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleCancel(task.id)}
                disabled={cancellingId === task.id}
                className="p-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
                title="Cancelar tarefa"
              >
                {cancellingId === task.id ? (
                  <div className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <p className="text-xs text-blue-700 dark:text-blue-400 text-center">
          🔔 As tarefas recorrentes apenas enviam lembretes. Nenhuma operação bancária é executada.
        </p>
      </div>
    </div>
  );
}
