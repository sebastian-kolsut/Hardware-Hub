<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  apiUrl: { type: String, required: true },
})

const STATUSES = ['Available', 'In Use', 'Repair']

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'brand', label: 'Brand' },
  { key: 'purchaseDate', label: 'Purchase Date' },
  { key: 'status', label: 'Status' },
]

const hardware = ref([])
const isLoading = ref(true)
const loadError = ref('')

const search = ref('')
const statusFilter = ref('All')
const sortKey = ref('name')
const sortDir = ref('asc')

onMounted(async () => {
  try {
    const response = await fetch(`${props.apiUrl}/api/hardware/`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    // API uses purchase_date; keep the rest of this component on the
    // camelCase shape it already had with the mock data.
    hardware.value = data.map((item) => ({ ...item, purchaseDate: item.purchase_date }))
  } catch (err) {
    loadError.value = `could not load hardware from ${props.apiUrl}: ${err.message}`
  } finally {
    isLoading.value = false
  }
})

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

const filteredSorted = computed(() => {
  const term = search.value.trim().toLowerCase()

  let rows = hardware.value.filter((item) => {
    const matchesSearch =
      !term ||
      item.name.toLowerCase().includes(term) ||
      item.brand.toLowerCase().includes(term)
    const matchesStatus = statusFilter.value === 'All' || item.status === statusFilter.value
    return matchesSearch && matchesStatus
  })

  rows = [...rows].sort((a, b) => {
    let cmp
    if (sortKey.value === 'purchaseDate') {
      cmp = new Date(a.purchaseDate) - new Date(b.purchaseDate)
    } else {
      cmp = a[sortKey.value].localeCompare(b[sortKey.value])
    }
    return sortDir.value === 'asc' ? cmp : -cmp
  })

  return rows
})

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function statusClass(status) {
  return {
    'status-available': status === 'Available',
    'status-in-use': status === 'In Use',
    'status-repair': status === 'Repair',
  }
}
</script>

<template>
  <section class="dashboard">
    <div class="page-header">
      <h1>Hardware List</h1>
    </div>

    <p v-if="isLoading" class="state-message">Loading hardware...</p>
    <p v-else-if="loadError" class="state-message error">{{ loadError }}</p>

    <template v-else>
      <div class="toolbar">
        <input
          v-model="search"
          type="text"
          placeholder="Search by name or brand..."
          class="search-input"
        />
        <select v-model="statusFilter" class="status-select">
          <option value="All">All statuses</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>

      <table class="hardware-table">
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              @click="toggleSort(col.key)"
              :class="{ active: sortKey === col.key }"
            >
              {{ col.label }}
              <span class="sort-indicator">
                {{ sortKey === col.key ? (sortDir === 'asc' ? '▲' : '▼') : '' }}
              </span>
            </th>
            <th class="actions-header">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredSorted" :key="item.id">
            <td class="name-cell">{{ item.name }}</td>
            <td>{{ item.brand }}</td>
            <td>{{ formatDate(item.purchaseDate) }}</td>
            <td>
              <span class="status-badge" :class="statusClass(item.status)">{{ item.status }}</span>
            </td>
            <td>
              <button class="rent-btn" disabled title="Coming soon">Rent</button>
            </td>
          </tr>
          <tr v-if="filteredSorted.length === 0">
            <td colspan="5" class="empty">No hardware matches your filters.</td>
          </tr>
        </tbody>
      </table>
    </template>
  </section>
</template>

<style scoped>
.dashboard {
  width: 100%;
  text-align: left;

  --badge-available-bg: #18181b;
  --badge-available-fg: #fafafa;
  --badge-inuse-bg: #52525b;
  --badge-inuse-fg: #fafafa;
  --badge-repair-bg: #dc2626;
  --badge-repair-fg: #fff5f5;
}

@media (prefers-color-scheme: dark) {
  .dashboard {
    --badge-available-bg: #e4e4e7;
    --badge-available-fg: #18181b;
    --badge-inuse-bg: #71717a;
    --badge-inuse-fg: #fafafa;
    --badge-repair-bg: #ef4444;
    --badge-repair-fg: #450a0a;
  }
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.75rem;
}

.page-header h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-h);
}

.toolbar {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.state-message {
  text-align: center;
  color: var(--text);
  padding: 2rem 0;
}

.state-message.error {
  color: #c0392b;
}

.search-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  font-size: 0.95rem;
  color: var(--text-h);
  background: var(--bg);
}

.status-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  font-size: 0.95rem;
  color: var(--text-h);
  background: var(--bg);
}

.hardware-table {
  width: 100%;
  border-collapse: collapse;
}

.hardware-table th,
.hardware-table td {
  padding: 0.7rem 0.75rem;
  border-bottom: 1px solid var(--border);
}

.hardware-table th {
  cursor: pointer;
  user-select: none;
  text-align: left;
  font-weight: 500;
  font-size: 0.82rem;
  color: var(--text);
  white-space: nowrap;
}

.hardware-table th.actions-header {
  cursor: default;
}

.hardware-table th.active {
  color: var(--text-h);
}

.name-cell {
  font-weight: 500;
  color: var(--text-h);
}

.sort-indicator {
  font-size: 0.7rem;
  color: var(--text);
}

.hardware-table tbody tr:hover {
  background: color-mix(in srgb, var(--text) 8%, transparent);
}

.empty {
  text-align: center;
  color: var(--text);
  padding: 1.5rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 500;
  border: 1px solid var(--border);
}

.status-available {
  background: var(--badge-available-bg);
  color: var(--badge-available-fg);
}

.status-in-use {
  background: var(--badge-inuse-bg);
  color: var(--badge-inuse-fg);
}

.status-repair {
  background: var(--badge-repair-bg);
  color: var(--badge-repair-fg);
}

.rent-btn {
  padding: 0.4rem 0.9rem;
  border: none;
  border-radius: 0.4rem;
  background: var(--text-h);
  color: var(--bg);
  font-size: 0.82rem;
  font-weight: 500;
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
