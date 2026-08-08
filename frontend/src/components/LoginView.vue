<script setup>
import { ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const { login } = useAuth()

const username = ref('')
const password = ref('')
const error = ref('')
const isSubmitting = ref(false)

async function handleSubmit() {
  error.value = ''
  isSubmitting.value = true
  try {
    await login(username.value, password.value)
  } catch (err) {
    error.value = err.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="login-screen">
    <form class="login-card" @submit.prevent="handleSubmit">
      <h1>Hardware Hub</h1>
      <p class="subtitle">Sign in to continue</p>

      <label class="field">
        <span>Username</span>
        <input v-model="username" type="text" autocomplete="username" required />
      </label>

      <label class="field">
        <span>Password</span>
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>

      <p v-if="error" class="error">{{ error }}</p>

      <button type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? 'Signing in...' : 'Sign in' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  width: 100%;
}

.login-card {
  width: 100%;
  max-width: 320px;
  padding: 2.25rem 2rem;
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.login-card h1 {
  margin: 0;
  font-size: 1.4rem;
}

.subtitle {
  margin: -0.5rem 0 0.25rem;
  color: var(--text);
  font-size: 0.9rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
  color: var(--text);
}

.field input {
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  font-size: 0.95rem;
  color: var(--text-h);
  background: var(--bg);
}

.error {
  color: #dc2626;
  font-size: 0.85rem;
  margin: 0;
}

button[type='submit'] {
  padding: 0.6rem 0.9rem;
  border: none;
  border-radius: 0.4rem;
  background: var(--text-h);
  color: var(--bg);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
}

button[type='submit']:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
