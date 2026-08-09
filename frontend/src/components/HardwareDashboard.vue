<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useApi } from '../composables/useApi'

const { isStaff } = useAuth()
const { apiFetch } = useApi()

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

function toApiFieldError(data) {
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  return Object.entries(data)
    .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(' ') : messages}`)
    .join(' | ')
}

onMounted(async () => {
  try {
    const response = await apiFetch('/api/hardware/')
    if (response.status === 401) return // useApi already cleared the session; App.vue swaps to the login screen
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    // API uses purchase_date; keep the rest of this component on the
    // camelCase shape it already had with the mock data.
    hardware.value = data.map((item) => ({ ...item, purchaseDate: item.purchase_date }))
  } catch (err) {
    loadError.value = `could not load hardware: ${err.message}`
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
  if (!dateStr) return '—'
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

// The API only ever sends item.rented_by when the viewer is entitled to see
// it (admin or the renter themselves) — a regular user viewing someone
// else's rental gets null here, so there's nothing to accidentally render.
function renterLabel(item) {
  if (item.status !== 'In Use') return ''
  if (item.rented_by_me) return 'Rented by you'
  if (isStaff.value && item.rented_by) return `Rented by ${item.rented_by}`
  return ''
}

// --- Rent / return (any authenticated user) ---

const rentingId = ref(null)
const returningId = ref(null)

function canRent(item) {
  return item.status === 'Available'
}

function canReturn(item) {
  // Backend enforces the same rule (renter or staff) — this only decides
  // whether to show the button; the request would 403 either way if wrong.
  return item.status === 'In Use' && (item.rented_by_me || isStaff.value)
}

async function rentItem(item) {
  rentingId.value = item.id
  try {
    const response = await apiFetch(`/api/hardware/${item.id}/rent/`, { method: 'POST' })
    const data = await response.json()
    if (!response.ok) throw new Error(toApiFieldError(data))
    Object.assign(item, { ...data, purchaseDate: data.purchase_date })
  } catch (err) {
    window.alert(`Could not rent "${item.name}": ${err.message}`)
  } finally {
    rentingId.value = null
  }
}

async function returnItem(item) {
  returningId.value = item.id
  try {
    const response = await apiFetch(`/api/hardware/${item.id}/return/`, { method: 'POST' })
    const data = await response.json()
    if (!response.ok) throw new Error(toApiFieldError(data))
    Object.assign(item, { ...data, purchaseDate: data.purchase_date })
  } catch (err) {
    window.alert(`Could not return "${item.name}": ${err.message}`)
  } finally {
    returningId.value = null
  }
}

// --- Admin: toggle a row's status to/from Repair ---

const statusUpdatingId = ref(null)

async function toggleRepair(item) {
  const nextStatus = item.status === 'Repair' ? 'Available' : 'Repair'
  statusUpdatingId.value = item.id
  try {
    const response = await apiFetch(`/api/hardware/${item.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ status: nextStatus }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(toApiFieldError(data))
    item.status = data.status
  } catch (err) {
    window.alert(`Could not update status: ${err.message}`)
  } finally {
    statusUpdatingId.value = null
  }
}

// --- Admin: approve a flagged row (clears needs_review without touching
// the other fields — fixing the underlying data is a separate, explicit
// step via Edit) ---

const approvingId = ref(null)

async function approveItem(item) {
  approvingId.value = item.id
  try {
    const response = await apiFetch(`/api/hardware/${item.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ needs_review: false }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(toApiFieldError(data))
    Object.assign(item, { ...data, purchaseDate: data.purchase_date })
  } catch (err) {
    window.alert(`Could not approve "${item.name}": ${err.message}`)
  } finally {
    approvingId.value = null
  }
}

// --- Admin: delete a row ---

async function deleteHardware(item) {
  if (!window.confirm(`Delete "${item.name}"? This cannot be undone.`)) return
  try {
    const response = await apiFetch(`/api/hardware/${item.id}/`, { method: 'DELETE' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    hardware.value = hardware.value.filter((row) => row.id !== item.id)
    // The edit form might be open on the row we just removed.
    if (editingItem.value?.id === item.id) closeHardwareForm()
  } catch (err) {
    window.alert(`Could not delete "${item.name}": ${err.message}`)
  }
}

// --- Admin: add/edit hardware form ---
//
// One form, one on-screen slot, two modes. Add and Edit both operate on the
// same fields and hit the same serializer shape on the backend (POST vs.
// PATCH to /api/hardware/), so a single form model plus a "what are we
// editing, if anything" flag avoids maintaining two near-identical forms.
// `editingItem` doubles as that flag: null means "add mode", a hardware row
// means "edit mode for this row". Opening one mode always closes the other,
// since the task calls for a single shared slot rather than two forms that
// could both be open simultaneously.

const isAddFormOpen = ref(false)
const editingItem = ref(null)
const isFormPanelOpen = computed(() => isAddFormOpen.value || editingItem.value !== null)

const hardwareForm = ref({ name: '', brand: '', purchaseDate: '', status: 'Available' })
const isSavingHardware = ref(false)
const hardwareFormError = ref('')

function openAddForm() {
  editingItem.value = null
  hardwareForm.value = { name: '', brand: '', purchaseDate: '', status: 'Available' }
  hardwareFormError.value = ''
  isAddFormOpen.value = true
}

function openEditForm(item) {
  isAddFormOpen.value = false
  hardwareFormError.value = ''
  editingItem.value = item
  hardwareForm.value = {
    name: item.name,
    brand: item.brand,
    purchaseDate: item.purchaseDate || '',
    status: item.status,
  }
}

function closeHardwareForm() {
  isAddFormOpen.value = false
  editingItem.value = null
  hardwareFormError.value = ''
}

async function handleSubmitHardwareForm() {
  hardwareFormError.value = ''
  isSavingHardware.value = true
  const payload = {
    name: hardwareForm.value.name,
    brand: hardwareForm.value.brand,
    purchase_date: hardwareForm.value.purchaseDate || null,
    status: hardwareForm.value.status,
  }
  try {
    const response = editingItem.value
      ? await apiFetch(`/api/hardware/${editingItem.value.id}/`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      : await apiFetch('/api/hardware/', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
    const data = await response.json()
    if (!response.ok) throw new Error(toApiFieldError(data))

    if (editingItem.value) {
      const target = hardware.value.find((row) => row.id === editingItem.value.id)
      if (target) Object.assign(target, { ...data, purchaseDate: data.purchase_date })
    } else {
      hardware.value.push({ ...data, purchaseDate: data.purchase_date })
    }
    closeHardwareForm()
  } catch (err) {
    hardwareFormError.value = err.message
  } finally {
    isSavingHardware.value = false
  }
}

// --- Admin: create user account form ---

const newUser = ref({ username: '', password: '', isStaff: false })
const isCreatingUser = ref(false)
const createUserError = ref('')
const createUserSuccess = ref('')

async function handleCreateUser() {
  createUserError.value = ''
  createUserSuccess.value = ''
  isCreatingUser.value = true
  try {
    const response = await apiFetch('/api/auth/users/', {
      method: 'POST',
      body: JSON.stringify({
        username: newUser.value.username,
        password: newUser.value.password,
        is_staff: newUser.value.isStaff,
      }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(toApiFieldError(data))
    createUserSuccess.value = `Created account for "${data.username}".`
    newUser.value = { username: '', password: '', isStaff: false }
  } catch (err) {
    createUserError.value = err.message
  } finally {
    isCreatingUser.value = false
  }
}
</script>

<template>
  <section class="dashboard">
    <div class="page-header">
      <h1>Hardware List</h1>
      <span class="mode-badge" :class="{ admin: isStaff }">
        {{ isStaff ? 'Admin view' : 'User view' }}
      </span>
    </div>

    <p v-if="isLoading" class="state-message">Loading hardware...</p>
    <p v-else-if="loadError" class="state-message error">{{ loadError }}</p>

    <template v-else>
      <section v-if="isStaff" class="admin-tools">
        <div class="admin-form">
          <div class="form-panel-header">
            <h2>{{ editingItem ? `Edit "${editingItem.name}"` : 'Add hardware' }}</h2>
            <button
              v-if="!isFormPanelOpen"
              type="button"
              class="admin-btn"
              @click="openAddForm"
            >
              + Add hardware
            </button>
          </div>

          <form v-if="isFormPanelOpen" @submit.prevent="handleSubmitHardwareForm">
            <div class="form-row">
              <input v-model.trim="hardwareForm.name" placeholder="Name" required />
              <input v-model.trim="hardwareForm.brand" placeholder="Brand" />
              <input v-model="hardwareForm.purchaseDate" type="date" />
              <select v-model="hardwareForm.status">
                <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
              </select>
              <button type="submit" :disabled="isSavingHardware">
                {{ isSavingHardware ? 'Saving...' : editingItem ? 'Save' : 'Add' }}
              </button>
              <button type="button" class="admin-btn" @click="closeHardwareForm">Cancel</button>
            </div>
            <p v-if="hardwareFormError" class="form-message error">{{ hardwareFormError }}</p>
          </form>
        </div>

        <form class="admin-form" @submit.prevent="handleCreateUser">
          <h2>Create user account</h2>
          <div class="form-row">
            <input v-model.trim="newUser.username" placeholder="Username" required />
            <input v-model="newUser.password" type="password" placeholder="Password" required />
            <label class="checkbox-label">
              <input v-model="newUser.isStaff" type="checkbox" />
              Admin
            </label>
            <button type="submit" :disabled="isCreatingUser">
              {{ isCreatingUser ? 'Creating...' : 'Create' }}
            </button>
          </div>
          <p v-if="createUserError" class="form-message error">{{ createUserError }}</p>
          <p v-if="createUserSuccess" class="form-message success">{{ createUserSuccess }}</p>
        </form>
      </section>

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

      <div class="table-wrapper">
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
            <tr
              v-for="item in filteredSorted"
              :key="item.id"
              :class="{ 'flagged-row': isStaff && item.needs_review }"
            >
              <td class="name-cell">
                {{ item.name }}
                <span
                  v-if="isStaff && item.needs_review"
                  class="review-badge"
                  :title="item.review_notes || 'Flagged for review'"
                >
                  Needs review
                </span>
              </td>
              <td>{{ item.brand }}</td>
              <td>{{ formatDate(item.purchaseDate) }}</td>
              <td>
                <span class="status-badge" :class="statusClass(item.status)">{{ item.status }}</span>
                <span v-if="renterLabel(item)" class="renter-label">{{ renterLabel(item) }}</span>
              </td>
              <td class="actions-cell">
                <button
                  v-if="canRent(item)"
                  class="rent-btn"
                  :disabled="rentingId === item.id"
                  @click="rentItem(item)"
                >
                  {{ rentingId === item.id ? 'Renting...' : 'Rent' }}
                </button>
                <button
                  v-else-if="canReturn(item)"
                  class="rent-btn"
                  :disabled="returningId === item.id"
                  @click="returnItem(item)"
                >
                  {{ returningId === item.id ? 'Returning...' : 'Return' }}
                </button>
                <button
                  v-else
                  class="rent-btn"
                  disabled
                  :title="item.status === 'In Use' ? 'Rented by someone else' : 'Not available to rent'"
                >
                  {{ item.status === 'In Use' ? 'Rented' : 'Unavailable' }}
                </button>
                <template v-if="isStaff">
                  <button
                    class="admin-btn"
                    :disabled="statusUpdatingId === item.id"
                    @click="toggleRepair(item)"
                  >
                    {{ item.status === 'Repair' ? 'Mark Available' : 'Send to Repair' }}
                  </button>
                  <button class="admin-btn" @click="openEditForm(item)">Edit</button>
                  <button
                    v-if="item.needs_review"
                    class="admin-btn approve"
                    :disabled="approvingId === item.id"
                    @click="approveItem(item)"
                  >
                    {{ approvingId === item.id ? 'Approving...' : 'Approve' }}
                  </button>
                  <button class="admin-btn danger" @click="deleteHardware(item)">Delete</button>
                </template>
              </td>
            </tr>
            <tr v-if="filteredSorted.length === 0">
              <td colspan="5" class="empty">No hardware matches your filters.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.dashboard {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  text-align: left;

  --badge-available-bg: #18181b;
  --badge-available-fg: #fafafa;
  --badge-inuse-bg: #52525b;
  --badge-inuse-fg: #fafafa;
  --badge-repair-bg: #dc2626;
  --badge-repair-fg: #fff5f5;
  --flag-bg: #fef3c7;
  --flag-fg: #92400e;
  --flag-row-bg: rgba(217, 119, 6, 0.08);
}

@media (prefers-color-scheme: dark) {
  .dashboard {
    --badge-available-bg: #e4e4e7;
    --badge-available-fg: #18181b;
    --badge-inuse-bg: #71717a;
    --badge-inuse-fg: #fafafa;
    --badge-repair-bg: #ef4444;
    --badge-repair-fg: #450a0a;
    --flag-bg: #78350f;
    --flag-fg: #fde68a;
    --flag-row-bg: rgba(217, 119, 6, 0.15);
  }
}

.page-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.75rem;
}

.page-header h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-h);
}

.mode-badge {
  padding: 0.25rem 0.7rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid var(--border);
  color: var(--text);
}

.mode-badge.admin {
  color: var(--accent);
  border-color: var(--accent-border);
  background: var(--accent-bg);
}

.admin-tools {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}

.admin-form {
  flex: 1 1 320px;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 1rem 1.1rem;
}

.admin-form h2 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-h);
}

.form-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.form-row input[type='text'],
.form-row input:not([type]),
.form-row input[type='password'],
.form-row input[type='date'] {
  flex: 1 1 120px;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  font-size: 0.88rem;
  color: var(--text-h);
  background: var(--bg);
}

.form-row select {
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  font-size: 0.88rem;
  color: var(--text-h);
  background: var(--bg);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  color: var(--text);
  white-space: nowrap;
}

.form-row button {
  padding: 0.45rem 0.9rem;
  border: none;
  border-radius: 0.375rem;
  background: var(--text-h);
  color: var(--bg);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
}

.form-row button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-message {
  margin: 0.6rem 0 0;
  font-size: 0.8rem;
}

.form-message.error {
  color: #c0392b;
}

.form-message.success {
  color: #15803d;
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

.table-wrapper {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
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

.hardware-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--bg);
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

.flagged-row {
  background: var(--flag-row-bg);
}

.review-badge {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  background: var(--flag-bg);
  color: var(--flag-fg);
  cursor: help;
}

.sort-indicator {
  font-size: 0.7rem;
  color: var(--text);
}

.hardware-table tbody tr:hover {
  background: color-mix(in srgb, var(--text) 8%, transparent);
}

.hardware-table tbody tr.flagged-row:hover {
  background: color-mix(in srgb, var(--flag-fg) 12%, var(--flag-row-bg));
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

.renter-label {
  display: block;
  margin-top: 0.3rem;
  font-size: 0.75rem;
  color: var(--text);
}

.actions-cell {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.rent-btn {
  padding: 0.4rem 0.9rem;
  border: none;
  border-radius: 0.4rem;
  background: var(--text-h);
  color: var(--bg);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
}

.rent-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.admin-btn {
  padding: 0.4rem 0.9rem;
  border: 1px solid var(--border);
  border-radius: 0.4rem;
  background: transparent;
  color: var(--text-h);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
}

.admin-btn:hover {
  border-color: var(--text-h);
}

.admin-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.admin-btn.danger {
  color: #dc2626;
  border-color: rgba(220, 38, 38, 0.4);
}

.admin-btn.danger:hover {
  border-color: #dc2626;
}

.admin-btn.approve {
  color: var(--flag-fg);
  border-color: var(--flag-fg);
}

.admin-btn.approve:hover {
  background: var(--flag-bg);
}
</style>
