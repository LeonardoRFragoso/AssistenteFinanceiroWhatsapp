import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000, // 30 segundos
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data: { name: string; email: string; password: string; phone_number: string }) =>
    api.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
  demoLogin: () => api.post('/auth/demo-login'),
  getMe: () => api.get('/auth/me'),
  checkAdminStatus: () => api.get('/auth/me/is-admin'),
};

export const transactionsAPI = {
  getAll: (limit = 100, offset = 0) =>
    api.get(`/transactions/?limit=${limit}&offset=${offset}`),
  getById: (id: number) => api.get(`/transactions/${id}`),
  create: (data: any) => api.post('/transactions/', data),
  update: (id: number, data: any) => api.put(`/transactions/${id}`, data),
  delete: (id: number) => api.delete(`/transactions/${id}`),
  getByDateRange: (startDate: string, endDate: string) =>
    api.get(`/transactions/date-range/?start_date=${startDate}&end_date=${endDate}`),
};

export const remindersAPI = {
  getAll: (includeCompleted = false) =>
    api.get(`/reminders/?include_completed=${includeCompleted}`),
  getUpcoming: (days = 7) => api.get(`/reminders/upcoming?days=${days}`),
  getById: (id: number) => api.get(`/reminders/${id}`),
  create: (data: any) => api.post('/reminders/', data),
  update: (id: number, data: any) => api.put(`/reminders/${id}`, data),
  markCompleted: (id: number) => api.post(`/reminders/${id}/complete`),
  delete: (id: number) => api.delete(`/reminders/${id}`),
};

export const reportsAPI = {
  getDashboard: () => api.get('/reports/dashboard'),
  getMonthly: (year: number, month: number) =>
    api.get(`/reports/monthly/${year}/${month}`),
  getCurrentMonth: () => api.get('/reports/current-month'),
  getPeriod: (startDate: string, endDate: string) =>
    api.get(`/reports/period?start_date=${startDate}&end_date=${endDate}`),
};

export const billingAPI = {
  getPlans: () => api.get('/billing/plans'),
  createCheckout: (planId: number) =>
    api.post('/billing/checkout', { plan_id: planId }),
  getPayments: () => api.get('/billing/payments'),
  getUsage: () => api.get('/billing/usage'),
  cancelSubscription: () => api.post('/billing/cancel-subscription'),
};

export const chargesAPI = {
  getAll: (limit = 50, status?: string) =>
    api.get(`/charges/?limit=${limit}${status ? `&status=${status}` : ''}`),
  getPaginated: (page = 1, pageSize = 20, status?: string, search?: string) => {
    let url = `/charges/?page=${page}&page_size=${pageSize}`;
    if (status) url += `&status=${status}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    return api.get(url);
  },
  getById: (id: number) => api.get(`/charges/${id}`),
  create: (data: any) => api.post('/charges/', data),
  cancel: (id: number) => api.post(`/charges/${id}/cancel`),
  getSummary: () => api.get('/charges/summary'),
  getAnalytics: () => api.get('/charges/analytics'),
  exportCSV: (status?: string, search?: string) => {
    let url = `/charges/export.csv`;
    const params: string[] = [];
    if (status) params.push(`status=${status}`);
    if (search) params.push(`search=${encodeURIComponent(search)}`);
    if (params.length) url += `?${params.join('&')}`;
    return api.get(url, { responseType: 'blob' });
  },
  exportPDF: (status?: string, search?: string) => {
    let url = `/charges/export.pdf`;
    const params: string[] = [];
    if (status) params.push(`status=${status}`);
    if (search) params.push(`search=${encodeURIComponent(search)}`);
    if (params.length) url += `?${params.join('&')}`;
    return api.get(url, { responseType: 'blob' });
  },
};

export const recurringTasksAPI = {
  list: () => api.get('/recurring-tasks'),
  create: (data: { title: string; description?: string; recurrence_type: string; day_of_week?: number; day_of_month?: number }) =>
    api.post('/recurring-tasks', data),
  cancel: (id: number) => api.post(`/recurring-tasks/${id}/cancel`),
};

export const documentsAPI = {
  analyze: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/documents/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const customersAPI = {
  list: (params?: { search?: string; status_filter?: string; has_overdue?: boolean; sort_by?: string; sort_order?: string; page?: number; page_size?: number }) => {
    let url = '/customers';
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status_filter) searchParams.append('status_filter', params.status_filter);
    if (params?.has_overdue !== undefined) searchParams.append('has_overdue', String(params.has_overdue));
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params?.sort_order) searchParams.append('sort_order', params.sort_order);
    if (params?.page) searchParams.append('page', String(params.page));
    if (params?.page_size) searchParams.append('page_size', String(params.page_size));
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
    return api.get(url);
  },
  getById: (id: number) => api.get(`/customers/${id}`),
  getCharges: (id: number) => api.get(`/customers/${id}/charges`),
  getSummary: (id: number) => api.get(`/customers/${id}/summary`),
  updateNotes: (id: number, notes: string) => api.patch(`/customers/${id}/notes`, { notes }),
};

export const messageTemplatesAPI = {
  list: (activeOnly?: boolean) => api.get(`/message-templates${activeOnly ? '?active_only=true' : ''}`),
  create: (data: { name: string; tone: string; template_text: string }) => api.post('/message-templates', data),
  update: (id: number, data: { name?: string; tone?: string; template_text?: string }) => api.put(`/message-templates/${id}`, data),
  preview: (id: number, data: { customer_name?: string; amount?: string; description?: string; due_date?: string; payment_link?: string }) =>
    api.post(`/message-templates/${id}/preview`, data),
  deactivate: (id: number) => api.post(`/message-templates/${id}/deactivate`),
};

export const collectionAPI = {
  listRules: () => api.get('/collection/rules'),
  createRule: (data: { name: string; days_offset: number; trigger_type: string; template_id?: number }) => api.post('/collection/rules', data),
  deactivateRule: (id: number) => api.post(`/collection/rules/${id}/deactivate`),
  getOverdueFollowups: (limit?: number) => api.get(`/collection/followups/overdue${limit ? `?limit=${limit}` : ''}`),
  listLogs: (limit?: number) => api.get(`/collection/logs${limit ? `?limit=${limit}` : ''}`),
};

export const analyticsAPI = {
  getOverview: (params?: { start_date?: string; end_date?: string }) => {
    let url = '/analytics/overview';
    const sp = new URLSearchParams();
    if (params?.start_date) sp.append('start_date', params.start_date);
    if (params?.end_date) sp.append('end_date', params.end_date);
    const qs = sp.toString();
    if (qs) url += `?${qs}`;
    return api.get(url);
  },
  getMonthlyTrends: (months?: number) => api.get(`/analytics/monthly-trends${months ? `?months=${months}` : ''}`),
  getAging: () => api.get('/analytics/aging'),
  getCustomerPerformance: (limit?: number) => api.get(`/analytics/customer-performance${limit ? `?limit=${limit}` : ''}`),
  getCollectionPerformance: () => api.get('/analytics/collection-performance'),
  getInsights: (params?: { start_date?: string; end_date?: string }) => {
    let url = '/analytics/insights';
    const sp = new URLSearchParams();
    if (params?.start_date) sp.append('start_date', params.start_date);
    if (params?.end_date) sp.append('end_date', params.end_date);
    const qs = sp.toString();
    if (qs) url += `?${qs}`;
    return api.get(url);
  },
  exportCSV: (params?: { start_date?: string; end_date?: string }) => {
    let url = '/analytics/export.csv';
    const sp = new URLSearchParams();
    if (params?.start_date) sp.append('start_date', params.start_date);
    if (params?.end_date) sp.append('end_date', params.end_date);
    const qs = sp.toString();
    if (qs) url += `?${qs}`;
    return api.get(url, { responseType: 'blob' });
  },
  exportPDF: (params?: { start_date?: string; end_date?: string }) => {
    let url = '/analytics/export.pdf';
    const sp = new URLSearchParams();
    if (params?.start_date) sp.append('start_date', params.start_date);
    if (params?.end_date) sp.append('end_date', params.end_date);
    const qs = sp.toString();
    if (qs) url += `?${qs}`;
    return api.get(url, { responseType: 'blob' });
  },
};

export const adminAPI = {
  getMetrics: () => api.get('/admin/metrics'),
  getFunnel: () => api.get('/admin/funnel'),
  getRetentionCohort: () => api.get('/admin/retention-cohort'),
  getConversion: () => api.get('/admin/conversion'),
  getRetention: (days = 30) => api.get(`/admin/retention?days=${days}`),
  getChurn: () => api.get('/admin/churn'),
  getLTV: () => api.get('/admin/ltv'),
  getDashboard: (cacEstimate = 50) => api.get(`/admin/dashboard?cac_estimate=${cacEstimate}`),
};

export const organizationsAPI = {
  list: () => api.get('/organizations'),
  create: (data: { name: string; document?: string; email?: string; phone?: string }) =>
    api.post('/organizations', data),
  get: (id: number) => api.get(`/organizations/${id}`),
  update: (id: number, data: { name?: string; document?: string; email?: string; phone?: string }) =>
    api.put(`/organizations/${id}`, data),
  listMembers: (orgId: number) => api.get(`/organizations/${orgId}/members`),
  addMember: (orgId: number, data: { email: string; role: string }) =>
    api.post(`/organizations/${orgId}/members`, data),
  updateMember: (orgId: number, memberId: number, data: { role: string }) =>
    api.put(`/organizations/${orgId}/members/${memberId}`, data),
  deactivateMember: (orgId: number, memberId: number) =>
    api.post(`/organizations/${orgId}/members/${memberId}/deactivate`),
};

export const saasBillingAPI = {
  getPlans: () => api.get('/saas-billing/plans'),
  getSubscription: () => api.get('/saas-billing/subscription'),
  getEntitlements: () => api.get('/saas-billing/entitlements'),
  getUsage: () => api.get('/saas-billing/usage'),
  changePlan: (planCode: string) =>
    api.post('/saas-billing/subscription/change-plan', { plan_code: planCode }),
  cancelSubscription: () => api.post('/saas-billing/subscription/cancel'),
  reactivateSubscription: () => api.post('/saas-billing/subscription/reactivate'),
  fakeCheckout: (planCode: string) =>
    api.post('/saas-billing/fake/checkout', { plan_code: planCode }),
};

export default api;
