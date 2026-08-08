import { computed, readonly, ref } from 'vue'
import { apiUrl } from '../config'

// A plain reactive module-level singleton rather than Pinia: the app has no
// router and no other shared state yet, so a whole state-management library
// would be a dependency added for one small bag of fields (token, username,
// is_staff). Refs declared at module scope are already shared and reactive
// across every component that imports this file — Pinia is a near-zero-cost
// upgrade later if more stores show up.
const STORAGE_KEY = 'hardwarehub_token'

const token = ref(localStorage.getItem(STORAGE_KEY))
const username = ref('')
const isStaff = ref(false)
const isReady = ref(false)

function persistToken(value) {
  token.value = value
  if (value) {
    localStorage.setItem(STORAGE_KEY, value)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

function clearSession() {
  persistToken(null)
  username.value = ''
  isStaff.value = false
}

async function login(usernameInput, password) {
  const response = await fetch(`${apiUrl}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: usernameInput, password }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || 'Login failed.')
  }

  persistToken(data.token)
  username.value = usernameInput
  isStaff.value = data.is_staff
}

async function logout() {
  if (token.value) {
    try {
      await fetch(`${apiUrl}/api/auth/logout/`, {
        method: 'POST',
        headers: { Authorization: `Token ${token.value}` },
      })
    } catch {
      // Best-effort server-side revocation — clear the local session regardless.
    }
  }
  clearSession()
}

// Validates a stored token against the backend instead of trusting it blindly
// (it may have been revoked, or the user object deleted, since it was saved).
async function restoreSession() {
  if (token.value) {
    try {
      const response = await fetch(`${apiUrl}/api/auth/me/`, {
        headers: { Authorization: `Token ${token.value}` },
      })
      if (!response.ok) throw new Error('invalid session')
      const data = await response.json()
      username.value = data.username
      isStaff.value = data.is_staff
    } catch {
      clearSession()
    }
  }
  isReady.value = true
}

export function useAuth() {
  return {
    username: readonly(username),
    isStaff: readonly(isStaff),
    isReady: readonly(isReady),
    isAuthenticated: computed(() => !!token.value),
    // Exposed (not readonly) so callers can attach it to Authorization headers.
    token,
    login,
    logout,
    restoreSession,
    clearSession,
  }
}
