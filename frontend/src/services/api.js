const API_BASE = 'http://localhost:8000';

export async function fetchJson(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || 'API request failed');
  }
  return response.json();
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
