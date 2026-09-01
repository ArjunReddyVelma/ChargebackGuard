const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

export async function login(email, password) {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail?.message || 'Login failed. Please check your credentials.');
  }
  return data;
}

export async function uploadBatch(file) {
  const formData = new FormData();
  formData.append('file', file);

  const token = localStorage.getItem('token');
  const res = await fetch(`${API_URL}/batches`, {
    method: 'POST',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    body: formData
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail?.message || 'Batch upload failed.');
  }
  return data;
}

export async function getMetrics(batchId = null) {
  const url = new URL(`${API_URL}/metrics`);
  if (batchId) url.searchParams.append('batch_id', batchId);

  const res = await fetch(url.toString(), {
    headers: getAuthHeaders()
  });

  const data = await res.json();
  if (!res.ok) throw new Error('Failed to fetch metrics.');
  return data;
}

export async function getTransactions(filters = {}) {
  const url = new URL(`${API_URL}/transactions`);
  Object.keys(filters).forEach(key => {
    if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
      url.searchParams.append(key, filters[key]);
    }
  });

  const res = await fetch(url.toString(), {
    headers: getAuthHeaders()
  });

  const data = await res.json();
  if (!res.ok) throw new Error('Failed to fetch transactions.');
  return data;
}

export async function getTransactionDetail(id) {
  const res = await fetch(`${API_URL}/transactions/${id}`, {
    headers: getAuthHeaders()
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail?.message || 'Failed to fetch transaction detail.');
  return data;
}

export async function submitDecision(id, decision, reason_text) {
  const res = await fetch(`${API_URL}/transactions/${id}/decision`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ decision, reason_text })
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail?.message || 'Failed to submit decision.');
  }
  return data;
}

export async function getConfig() {
  const res = await fetch(`${API_URL}/config`, {
    headers: getAuthHeaders()
  });

  const data = await res.json();
  if (!res.ok) throw new Error('Failed to fetch config.');
  return data;
}

export async function updateConfig(configData) {
  const res = await fetch(`${API_URL}/config`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(configData)
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail?.message || 'Failed to update config.');
  return data;
}

export async function getAuditLog(eventType = null) {
  const url = new URL(`${API_URL}/audit-log`);
  if (eventType) url.searchParams.append('event_type', eventType);

  const res = await fetch(url.toString(), {
    headers: getAuthHeaders()
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail?.message || 'Failed to fetch audit log.');
  return data;
}
