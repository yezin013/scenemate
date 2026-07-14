export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function apiFetch(path, token, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(`${API}${path}`, { ...options, headers })
}
