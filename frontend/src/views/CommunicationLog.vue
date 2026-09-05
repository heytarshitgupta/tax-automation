<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const messages = ref([])
const loading = ref(true)
const errorMsg = ref('')
const statusFilter = ref('')

const statusOptions = ['PENDING', 'SENT', 'FAILED', 'DELIVERED', 'READ']

async function loadHistory() {
  loading.value = true
  errorMsg.value = ''
  const params = {}
  if (statusFilter.value) params.status_filter = statusFilter.value

  const { data, error } = await api.getMessageHistory(params)
  if (error) {
    errorMsg.value = error.message
  } else {
    messages.value = data
  }
  loading.value = false
}

function badgeClass(status) {
  switch (status) {
    case 'SENT':
    case 'DELIVERED':
    case 'READ':
      return 'badge badge-success'
    case 'FAILED':
      return 'badge badge-danger'
    default:
      return 'badge badge-warning'
  }
}

function formatDate(ts) {
  const d = new Date(ts)
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function messageTypeLabel(type) {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

onMounted(loadHistory)
</script>

<template>
  <div>
    <div class="page-header header-row">
      <div>
        <h1>Communication Log</h1>
        <p>Track every WhatsApp message sent to clients: reminders, requests, and notifications.</p>
      </div>
      <select v-model="statusFilter" @change="loadHistory" style="width: 200px; padding: 9px 12px; border-radius: 8px; border: 1px solid var(--border)">
        <option value="">All Statuses</option>
        <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>

    <div v-if="errorMsg" class="alert alert-error">{{ errorMsg }}</div>

    <div class="card" style="padding: 0">
      <div v-if="loading" class="loading-state">Loading communication log...</div>
      <div v-else-if="messages.length === 0" class="empty-state">
        No messages found for the selected filter.
      </div>
      <table v-else>
        <thead>
          <tr>
            <th>Client</th>
            <th>Message Type</th>
            <th>Content</th>
            <th>Sent At</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="msg in messages" :key="msg.id">
            <td>{{ msg.client?.business_name || `Client #${msg.client_id}` }}</td>
            <td>{{ messageTypeLabel(msg.message_type) }}</td>
            <td style="max-width: 320px; white-space: normal">{{ msg.message_content || '—' }}</td>
            <td>{{ formatDate(msg.sent_timestamp) }}</td>
            <td><span :class="badgeClass(msg.status)">{{ msg.status }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
</style>
