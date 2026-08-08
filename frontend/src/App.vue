<script setup>
import { onMounted, ref } from 'vue'

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
    <h1>Hardware Hub</h1>
    <p :class="{ error: isError }">{{ status }}</p>
  </main>
</template>

<style scoped>
main {
  font-family: system-ui, sans-serif;
  max-width: 32rem;
  margin: 4rem auto;
  text-align: center;
}

.error {
  color: #c0392b;
}
</style>
