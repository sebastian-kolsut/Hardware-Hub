import { apiUrl } from '../config'
import { useAuth } from './useAuth'

// Single place that attaches the auth token to every request and reacts to
// the backend saying it's no longer valid, so call sites never touch
// Authorization headers or 401 handling themselves.
export function useApi() {
  const { token, clearSession } = useAuth()

  async function apiFetch(path, options = {}) {
    const headers = { ...(options.headers || {}) }
    if (token.value) {
      headers.Authorization = `Token ${token.value}`
    }
    if (options.body && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }

    const response = await fetch(`${apiUrl}${path}`, { ...options, headers })
    if (response.status === 401) {
      clearSession()
    }
    return response
  }

  return { apiFetch }
}
