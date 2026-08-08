<script setup>
import { onMounted, ref } from 'vue'
import HardwareDashboard from './components/HardwareDashboard.vue'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const status = ref('checking...')
const isError = ref(false)

onMounted(async () => {
  try {
    const response = await fetch(`${apiUrl}/api/ping/`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    status.value = `backend says: ${data.status}`
  } catch (err) {
    isError.value = true
    status.value = `could not reach backend at ${apiUrl} (${err.message})`
  }
})
</script>

<template>
  <main>
    <header>
      <h1>Hardware Hub</h1>
      <p class="backend-status" :class="{ error: isError }">{{ status }}</p>
    </header>
    <HardwareDashboard />
  </main>
</template>

<style scoped>
main {
  font-family: system-ui, sans-serif;
  max-width: 60rem;
  margin: 3rem auto;
  padding: 0 1.5rem;
}

header {
  text-align: center;
  margin-bottom: 2rem;
}

.backend-status {
  font-size: 0.85rem;
  color: #888;
}

.backend-status.error {
  color: #c0392b;
}
</style>
