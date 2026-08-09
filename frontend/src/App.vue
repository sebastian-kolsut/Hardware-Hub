<script setup>
import { onMounted, ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import HardwareDashboard from './components/HardwareDashboard.vue'
import LoginView from './components/LoginView.vue'
import { useAuth } from './composables/useAuth'
import { apiUrl } from './config'

const status = ref('checking backend...')
const isError = ref(false)
const scope = ref('all')

const { isAuthenticated, isReady, username, isStaff, restoreSession, logout } = useAuth()

onMounted(async () => {
  await restoreSession()

  try {
    const response = await fetch(`${apiUrl}/api/ping/`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    await response.json()
    status.value = 'backend connected'
  } catch (err) {
    isError.value = true
    status.value = `backend unreachable (${err.message})`
  }
})
</script>

<template>
  <div v-if="!isReady" class="boot-loading">Loading...</div>
  <LoginView v-else-if="!isAuthenticated" />
  <div v-else class="shell">
    <Sidebar
      :status-text="status"
      :is-error="isError"
      :username="username"
      :is-staff="isStaff"
      :scope="scope"
      @logout="logout"
      @navigate="scope = $event"
    />
    <main>
      <HardwareDashboard :scope="scope" />
    </main>
  </div>
</template>

<style scoped>
.boot-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  color: var(--text);
  font-family: system-ui, sans-serif;
}

.shell {
  display: flex;
  align-items: stretch;
  height: 100vh;
  font-family: system-ui, sans-serif;
}

main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 2.5rem 3rem;
}
</style>
