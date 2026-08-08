<script setup>
import { onMounted, ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import HardwareDashboard from './components/HardwareDashboard.vue'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const status = ref('checking backend...')
const isError = ref(false)

onMounted(async () => {
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
  <div class="shell">
    <Sidebar :status-text="status" :is-error="isError" />
    <main>
      <HardwareDashboard :api-url="apiUrl" />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  align-items: stretch;
  min-height: 100vh;
  font-family: system-ui, sans-serif;
}

main {
  flex: 1;
  min-width: 0;
  padding: 2.5rem 3rem;
}
</style>
