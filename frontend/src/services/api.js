function getApiBaseUrl() {
  const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/$/, '');
  }

  // Local development / preview on localhost or 127.0.0.1
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0') {
      return 'http://localhost:8000';
    }
  }

  return '';
}

const API_BASE_URL = getApiBaseUrl();

export async function fetchJson(endpoint, options = {}) {
  // Guard against missing backend configuration on cloud deployments
  if (!API_BASE_URL && typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    throw new Error('Backend URL (VITE_API_BASE_URL) is not set in Vercel Environment Variables. Set VITE_API_BASE_URL in Vercel and redeploy.');
  }

  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: null }));
      const errorMsg = err.detail || `HTTP ${response.status} (${response.statusText || 'Error'}) from ${url}`;
      throw new Error(errorMsg);
    }

    return response.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Cannot reach backend at ${url}. If using Render free tier, the backend may be waking up from sleep.`);
    }
    throw err;
  }
}

export const api = {
  getSystemStatus: () => fetchJson('/'),
  getHealth: () => fetchJson('/health'),
  
  // Agent
  runAgent: (payload) => fetchJson('/agent/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  approveOrder: (payload) => fetchJson('/agent/approve', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getAgentRuns: () => fetchJson('/agent/runs'),
  getAgentRunDetail: (runId) => fetchJson(`/agent/runs/${runId}`),

  // Inventory
  getInventory: () => fetchJson('/inventory'),
  getProducts: () => fetchJson('/inventory'),
  getProduct: (id) => fetchJson(`/inventory/product/${id}`),
  updateProduct: (id, updates) => fetchJson(`/inventory/product/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  }),
  restockProduct: (payload) => fetchJson('/inventory/restock', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getLowStockEvents: () => fetchJson('/inventory/low-stock-events'),
  getInventoryLogs: () => fetchJson('/inventory/logs'),

  // Orders
  getOrders: (status) => fetchJson(status ? `/orders?status=${status}` : '/orders'),
  getOrder: (id) => fetchJson(`/orders/${id}`),
  getPendingApprovals: () => fetchJson('/orders/pending-approvals'),
};
