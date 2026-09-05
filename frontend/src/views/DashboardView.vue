<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const metrics = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const triggering = ref(false)
const triggerMsg = ref('')

async function loadMetrics() {
  loading.value = true
  errorMsg.value = ''
  const { data, error } = await api.getDashboardMetrics()
  if (error) {
    errorMsg.value = error.message
  } else {
    metrics.value = data
  }
  loading.value = false
}

async function runSchedulerNow() {
  triggering.value = true
  triggerMsg.value = ''
  const { error } = await api.runSchedulerNow()
  if (error) {
    triggerMsg.value = `Failed to run job: ${error.message}`
  } else {
    triggerMsg.value = 'Compliance reminder job executed successfully.'
    await loadMetrics()
  }
  triggering.value = false
}

onMounted(loadMetrics)
</script>

<template>
  <div>
    <div class="page-header">
      <h1>Dashboard</h1>
      <p>Overview of client engagement and WhatsApp automation performance.</p>
    </div>

    <div v-if="errorMsg" class="alert alert-error">{{ errorMsg }}</div>
    <div v-if="triggerMsg" class="alert alert-success">{{ triggerMsg }}</div>

    <div v-if="loading" class="loading-state">Loading metrics...</div>

    <template v-else-if="metrics">
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon icon-blue">👥</div>
          <div>
            <div class="metric-value">{{ metrics.total_clients }}</div>
            <div class="metric-label">Total Clients</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon icon-green">✅</div>
          <div>
            <div class="metric-value">{{ metrics.active_clients }}</div>
            <div class="metric-label">Active Clients</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon icon-gray">⏸</div>
          <div>
            <div class="metric-value">{{ metrics.inactive_clients }}</div>
            <div class="metric-label">Inactive Clients</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon icon-whatsapp">💬</div>
          <div>
            <div class="metric-value">{{ metrics.messages_sent_today }}</div>
            <div class="metric-label">Messages Sent Today</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon icon-red">⚠️</div>
          <div>
            <div class="metric-value">{{ metrics.messages_failed_today }}</div>
            <div class="metric-label">Failed Today</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon icon-orange">📅</div>
          <div>
            <div class="metric-value">{{ metrics.upcoming_compliance_7_days }}</div>
            <div class="metric-label">Due Within 7 Days</div>
          </div>
        </div>
      </div>

      <div class="card action-card">
        <div>
          <h3>Automation Engine</h3>
          <p style="color: var(--text-muted); margin: 0; font-size: 14px">
            The scheduler runs automatically every day at 09:00 to send GST/TDS reminders for
            compliance dates due in 7, 3, and 1 day(s). You can also trigger it manually below for
            testing/demo purposes.
          </p>
        </div>
        <button class="btn btn-primary" :disabled="triggering" @click="runSchedulerNow">
          {{ triggering ? 'Running...' : 'Run Reminder Job Now' }}
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.metric-icon {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.icon-blue { background: #dbeafe; }
.icon-green { background: #dcfce7; }
.icon-gray { background: #e2e8f0; }
.icon-whatsapp { background: #dcf8e8; }
.icon-red { background: #fee2e2; }
.icon-orange { background: #fef3c7; }

.metric-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
}

.metric-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 2px;
}

.action-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}
</style>
