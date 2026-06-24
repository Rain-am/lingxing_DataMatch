const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!response.ok) {
    let detail = await response.text()
    try {
      detail = JSON.parse(detail).detail || detail
    } catch {
      // keep raw text
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json()
}

export function listRules() {
  return request('/api/rules')
}

export function createRule(rule) {
  return request('/api/rules', { method: 'POST', body: JSON.stringify(rule) })
}

export function updateRule(id, rule) {
  return request(`/api/rules/${id}`, { method: 'PUT', body: JSON.stringify(rule) })
}

export function deleteRule(id) {
  return request(`/api/rules/${id}`, { method: 'DELETE' })
}

export function runReconcile(payload) {
  return request('/api/reconcile/run', { method: 'POST', body: JSON.stringify(payload) })
}

export function exportRunUrl(runId) {
  return `${API_BASE}/api/reconcile/runs/${runId}/export`
}
