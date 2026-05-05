const BASE = import.meta.env.VITE_API_URL || ''

// ── Token helpers ─────────────────────────────────────────────────────────
export function getToken()             { return localStorage.getItem('token') }
export function getUsername()          { return localStorage.getItem('username') }
export function setAuth(token, user)   { localStorage.setItem('token', token); localStorage.setItem('username', user) }
export function clearAuth()            { localStorage.removeItem('token'); localStorage.removeItem('username') }
export function isLoggedIn()           { return !!getToken() }

function authHeaders() {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function handleResponse(res) {
  if (res.status === 401) { clearAuth(); window.location.reload() }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || res.statusText)
  }
  return res.json()
}

// ── Auth endpoints ────────────────────────────────────────────────────────
export async function register(username, password) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return handleResponse(res)
}

export async function login(username, password) {
  const form = new URLSearchParams({ username, password })
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  })
  const data = await handleResponse(res)
  setAuth(data.access_token, data.username)
  return data
}

export function logout() { clearAuth() }

export async function fetchUsage() {
  const res = await fetch(`${BASE}/auth/usage`, { headers: authHeaders() })
  return handleResponse(res)
}

// ── Pipeline endpoints ────────────────────────────────────────────────────
export async function startAnalysis(videoUrl, maxComments, threshold) {
  const res = await fetch(`${BASE}/analyse`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ video_url: videoUrl, max_comments: maxComments, threshold }),
  })
  return handleResponse(res)
}

export async function pollStatus(jobId) {
  const res = await fetch(`${BASE}/status/${jobId}`, { headers: authHeaders() })
  return handleResponse(res)
}

export async function fetchComments(jobId, sentiment = null, limit = 50) {
  const params = new URLSearchParams({ limit })
  if (sentiment) params.set('sentiment', sentiment)
  const res = await fetch(`${BASE}/comments/${jobId}?${params}`, { headers: authHeaders() })
  return handleResponse(res)
}

export async function fetchHistory() {
  const res = await fetch(`${BASE}/history`, { headers: authHeaders() })
  return handleResponse(res)
}