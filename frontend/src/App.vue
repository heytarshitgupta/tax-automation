<script setup>
import { ref, onMounted } from 'vue'
import { RouterView, RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const isDark = ref(false)

function toggleTheme() {
  isDark.value = !isDark.value
  const theme = isDark.value ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('theme', theme)
}

onMounted(() => {
  const savedTheme = localStorage.getItem('theme') || 'light'
  isDark.value = savedTheme === 'dark'
  document.documentElement.setAttribute('data-theme', savedTheme)
})
</script>

<template>
  <div class="app-shell">
    <!-- ============================= SIDEBAR ============================= -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-logo">GS</div>
        <div>
          <div class="brand-name">Gateway Solutions</div>
          <div class="brand-sub">Tax Office Automation</div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <RouterLink to="/" class="nav-item" :class="{ active: route.name === 'dashboard' }">
          <span class="nav-icon">📊</span> Dashboard
        </RouterLink>
        <RouterLink to="/clients" class="nav-item" :class="{ active: route.name === 'clients' }">
          <span class="nav-icon">👥</span> Clients
        </RouterLink>
        <RouterLink
          to="/communication-log"
          class="nav-item"
          :class="{ active: route.name === 'communication-log' }"
        >
          <span class="nav-icon">💬</span> Communication Log
        </RouterLink>
      </nav>

      <div class="sidebar-footer">
        <button class="theme-toggle-btn" @click="toggleTheme">
          <span class="nav-icon">{{ isDark ? '☀️' : '🌙' }}</span>
          <span>{{ isDark ? 'Light Mode' : 'Dark Mode' }}</span>
        </button>
        <div class="status-indicator">
          <div class="status-dot"></div>
          WhatsApp Automation Active
        </div>
      </div>
    </aside>

    <!-- ============================= MAIN CONTENT ============================= -->
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 250px;
  flex-shrink: 0;
  background: linear-gradient(180deg, #075e54, #054d44);
  color: #fff;
  display: flex;
  flex-direction: column;
  padding: 24px 16px;
  position: sticky;
  top: 0;
  height: 100vh;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 8px 24px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
  margin-bottom: 20px;
}

.brand-logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #25d366;
  color: #054d44;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
}

.brand-name {
  font-weight: 600;
  font-size: 15px;
}

.brand-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.15s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.nav-item.active {
  background: #25d366;
  color: #05372f;
}

.nav-icon {
  font-size: 16px;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
}

.theme-toggle-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 12px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.theme-toggle-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #25d366;
  box-shadow: 0 0 0 3px rgba(37, 211, 102, 0.25);
}

.main-content {
  flex: 1;
  padding: 32px 40px;
  max-width: 1200px;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}
</style>
