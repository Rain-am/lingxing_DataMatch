const API_BASE = import.meta.env.VITE_API_BASE || ''

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

export function batchRunReconcile(payload) {
  return request('/api/reconcile/batch-run', { method: 'POST', body: JSON.stringify(payload) })
}

export function listRuns(params = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  }
  return request(`/api/reconcile/runs${query.toString() ? `?${query}` : ''}`)
}

export function getRun(runId) {
  return request(`/api/reconcile/runs/${runId}`)
}

export function exportRunUrl(runId) {
  return `${API_BASE}/api/reconcile/runs/${runId}/export`
}

export async function exportCompareRuns(runIds) {
  const response = await fetch(`${API_BASE}/api/reconcile/runs/compare/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_ids: runIds }),
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
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'reconcile-compare.xlsx'
  link.click()
  URL.revokeObjectURL(url)
}
