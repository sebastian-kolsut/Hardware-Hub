<script setup>
import { computed, ref } from 'vue'
import { mockHardware } from '../data/mockHardware.js'

const STATUSES = ['Available', 'In Use', 'Repair']

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'brand', label: 'Brand' },
  { key: 'purchaseDate', label: 'Purchase Date' },
  { key: 'status', label: 'Status' },
]

const search = ref('')
const statusFilter = ref('All')
const sortKey = ref('name')
const sortDir = ref('asc')

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

  let rows = mockHardware.filter((item) => {
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
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in filteredSorted" :key="item.id">
          <td>{{ item.name }}</td>
          <td>{{ item.brand }}</td>
          <td>{{ formatDate(item.purchaseDate) }}</td>
          <td>
            <span class="status-badge" :class="statusClass(item.status)">{{ item.status }}</span>
          </td>
        </tr>
        <tr v-if="filteredSorted.length === 0">
          <td colspan="4" class="empty">No hardware matches your filters.</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.dashboard {
  width: 100%;
  max-width: 56rem;
  margin: 0 auto;
  text-align: left;
}

.toolbar {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
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
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--border);
}

.hardware-table th {
  cursor: pointer;
  user-select: none;
  text-align: left;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
}

.hardware-table th.active {
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
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-available {
  background: #e3f6e8;
  color: #1e7d3c;
}

.status-in-use {
  background: #e5f0fd;
  color: #1a5bb8;
}

.status-repair {
  background: #fdecea;
  color: #c0392b;
}
</style>
