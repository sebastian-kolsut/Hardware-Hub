<script setup>
defineProps({
  statusText: { type: String, default: '' },
  isError: { type: Boolean, default: false },
})
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <svg class="brand-icon" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M21 8l-9-5-9 5 9 5 9-5z" stroke-linejoin="round" />
        <path d="M3 8v8l9 5 9-5V8" stroke-linejoin="round" />
      </svg>
      <span class="brand-name">Hardware Hub</span>
    </div>

    <nav class="nav">
      <div class="nav-item active">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8">
          <line x1="8" y1="6" x2="21" y2="6" />
          <line x1="8" y1="12" x2="21" y2="12" />
          <line x1="8" y1="18" x2="21" y2="18" />
          <line x1="3" y1="6" x2="3.01" y2="6" />
          <line x1="3" y1="12" x2="3.01" y2="12" />
          <line x1="3" y1="18" x2="3.01" y2="18" />
        </svg>
        Hardware List
      </div>
      <div class="nav-item disabled" title="Coming soon">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="12" cy="12" r="9" />
          <polyline points="12 7 12 12 15 15" />
        </svg>
        My Rentals
      </div>
      <div class="nav-item disabled" title="Coming soon">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="12" cy="12" r="3" />
          <path
            d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.6a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z"
          />
        </svg>
        Admin Panel
      </div>
    </nav>

    <div class="footer">
      <span class="status-dot" :class="{ error: isError }" />
      <span class="status-text">{{ statusText }}</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  padding: 1.75rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  box-sizing: border-box;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.brand-icon {
  color: var(--text-h);
  flex-shrink: 0;
}

.brand-name {
  font-weight: 600;
  font-size: 1.05rem;
  color: var(--text-h);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.55rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  color: var(--text);
}

.nav-item svg {
  flex-shrink: 0;
}

.nav-item.active {
  background: var(--text-h);
  color: var(--bg);
  font-weight: 500;
}

.nav-item.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text);
}

.status-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  background: #22c55e;
  flex-shrink: 0;
}

.status-dot.error {
  background: #ef4444;
}
</style>
