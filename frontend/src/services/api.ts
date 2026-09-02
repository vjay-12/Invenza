/**
 * Invenza API Client
 * Connects React frontend to FastAPI backend endpoints.
 * Automatically handles JWT authentication, Super Admin operations, and Tenant isolation.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

export function getAuthToken(): string | null {
  return localStorage.getItem('invenza_token');
}

export async function fetchWithFallback<T>(url: string, options?: RequestInit): Promise<T | null> {
  try {
    const token = getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers as Record<string, string> || {}),
    };

    const res = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      if (res.status === 403) {
        throw new Error(errBody.detail || 'Access Forbidden: Company account deactivated or insufficient permissions.');
      }
      console.warn(`API response status ${res.status} on ${url}:`, errBody);
      return null;
    }
    return await res.json();
  } catch (err: any) {
    if (err?.message && err.message.includes('Access Forbidden')) {
      throw err;
    }
    console.warn(`Backend call failed for ${url}, fallback to local store:`, err);
    return null;
  }
}

export const api = {
  // Auth
  login: async (credentials: { email: string; password: string }) => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Login failed. Please check your credentials.');
      }
      return await res.json();
    } catch (err: any) {
      throw err;
    }
  },

  getCurrentUser: async () => fetchWithFallback<any>('/auth/me'),

  // Super Admin Endpoints
  getCompanies: async (search?: string, industry?: string, activeOnly?: boolean) => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (industry && industry !== 'all') params.append('industry', industry);
    if (activeOnly !== undefined) params.append('active_only', String(activeOnly));
    const qs = params.toString() ? `?${params.toString()}` : '';
    return fetchWithFallback<any[]>(`/superadmin/companies${qs}`);
  },

  provisionCompany: async (data: {
    company_name: string;
    industry: string;
    location: string;
    currency_code: string;
    admin_full_name: string;
    admin_email: string;
    admin_password: string;
    enabled_modules: string[];
    send_email: boolean;
  }) => {
    const token = getAuthToken();
    const res = await fetch(`${API_BASE_URL}/superadmin/companies`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to provision company.');
    }
    return await res.json();
  },

  updateCompany: async (companyId: string, data: any) =>
    fetchWithFallback<any>(`/superadmin/companies/${companyId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  toggleCompanyStatus: async (companyId: string) =>
    fetchWithFallback<any>(`/superadmin/companies/${companyId}/toggle-status`, {
      method: 'PATCH',
    }),

  getCompanyAnalytics: async (companyId: string) =>
    fetchWithFallback<any>(`/superadmin/companies/${companyId}/analytics`),

  getPlatformReport: async () =>
    fetchWithFallback<any>('/superadmin/reports/platform'),

  // Company Team & Users
  getCompanyUsers: async () => fetchWithFallback<any[]>('/company/users/'),

  createCompanyUser: async (data: {
    full_name: string;
    email: string;
    password: string;
    role: string;
    permissions: string[];
    send_email: boolean;
  }) => {
    const token = getAuthToken();
    const res = await fetch(`${API_BASE_URL}/company/users/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create user.');
    }
    return await res.json();
  },

  updateCompanyUser: async (userId: string, data: any) =>
    fetchWithFallback<any>(`/company/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteCompanyUser: async (userId: string) =>
    fetchWithFallback<any>(`/company/users/${userId}`, {
      method: 'DELETE',
    }),

  // Health
  checkHealth: async () => fetchWithFallback<{ status: string }>('/health'),

  // Products
  getProducts: async () => fetchWithFallback<any[]>('/products/'),
  createProduct: async (data: any) =>
    fetchWithFallback<any>('/products/', { method: 'POST', body: JSON.stringify(data) }),
  bulkCreateProducts: async (data: any[]) =>
    fetchWithFallback<any[]>('/products/bulk-import', { method: 'POST', body: JSON.stringify(data) }),

  // Locations
  getLocations: async () => fetchWithFallback<any[]>('/locations/'),
  createLocation: async (data: any) =>
    fetchWithFallback<any>('/locations/', { method: 'POST', body: JSON.stringify(data) }),

  // Ledger
  getMovements: async () => fetchWithFallback<any[]>('/ledger/'),

  // Orders
  getPurchaseOrders: async () => fetchWithFallback<any[]>('/orders/purchase-orders'),
  receiveGoodsGRN: async (poId: string, notes?: string) =>
    fetchWithFallback<any>(`/orders/purchase-orders/${poId}/receive`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    }),

  // MinIO Storage
  checkStorageHealth: async () => fetchWithFallback<any>('/storage/health'),
  listStoredFiles: async () => fetchWithFallback<any[]>('/storage/list'),
  uploadFile: async (formData: FormData) => {
    try {
      const token = getAuthToken();
      const res = await fetch(`${API_BASE_URL}/storage/upload`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        throw new Error(`Upload failed: status ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.error('Storage upload error:', err);
      throw err;
    }
  },

  // AI Copilot
  chatWithCopilot: async (messages: { role: string; content: string }[]) =>
    fetchWithFallback<any>('/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({ messages }),
    }),
};
