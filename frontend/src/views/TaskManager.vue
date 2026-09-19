<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import api from '../services/api'

// ---------------------------------------------------------------
// STATE MANAGEMENT
// ---------------------------------------------------------------
const tasks = ref([])
const clients = ref([])
const staffList = ref([])
const metrics = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const toast = reactive({ show: false, message: '', type: 'success' })

// Filter & Search state
const searchQuery = ref('')
const statusFilter = ref('ALL')
const staffFilter = ref('ALL')
const overdueOnly = ref(false)
const sortBy = ref('due_date') // 'due_date', 'date_assigned', 'matter', 'client'
const sortOrder = ref('asc') // 'asc', 'desc'

let searchDebounceTimer = null

// Modal / Drawer state
const isDrawerOpen = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const formErrors = reactive({})

const defaultFormData = () => ({
  id: null,
  client_id: '',
  matter: '',
  assigned_staff: '',
  date_assigned: new Date().toISOString().split('T')[0],
  due_date: '',
  next_followup_date: '',
  status: 'PENDING',
  remarks: '',
  documents: '',
})

const formData = reactive(defaultFormData())

// WhatsApp Reminder Modal state
const isReminderModalOpen = ref(false)
const activeReminderTask = ref(null)
const customReminderMessage = ref('')
const sendingReminder = ref(false)
const reminderResult = ref(null)

// Delete Confirmation Modal state
const isDeleteModalOpen = ref(false)
const taskToDelete = ref(null)
const deleting = ref(false)

// ---------------------------------------------------------------
// HELPER FUNCTIONS & DATE UTILS
// ---------------------------------------------------------------
function showToast(message, type = 'success') {
  toast.message = message
  toast.type = type
  toast.show = true
  setTimeout(() => {
    toast.show = false
  }, 4000)
}

function getTodayString() {
  return new Date().toISOString().split('T')[0]
}

function parseDateOnly(dateStr) {
  if (!dateStr) return null
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function isOverdue(task) {
  if (!task.due_date) return false
  if (task.status === 'COMPLETED' || task.status === 'CANCELLED') return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const taskDue = parseDateOnly(task.due_date)
  return taskDue < today
}

function isDueToday(task) {
  if (!task.due_date) return false
  if (task.status === 'COMPLETED' || task.status === 'CANCELLED') return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const taskDue = parseDateOnly(task.due_date)
  return taskDue.getTime() === today.getTime()
}

function daysOverdue(task) {
  if (!task.due_date) return 0
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const taskDue = parseDateOnly(task.due_date)
  const diffTime = today.getTime() - taskDue.getTime()
  return Math.max(1, Math.floor(diffTime / (1000 * 60 * 60 * 24)))
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const [y, m, d] = dateStr.split('-').map(Number)
  const dt = new Date(y, m - 1, d)
  return dt.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

// ---------------------------------------------------------------
// STATUS CONFIGURATION
// ---------------------------------------------------------------
const STATUS_CONFIG = {
  PENDING: {
    label: 'Pending',
    icon: '⏳',
    colorClass: 'status-pending',
    badgeClass: 'badge-pending',
  },
  IN_PROGRESS: {
    label: 'In Progress',
    icon: '🔄',
    colorClass: 'status-in-progress',
    badgeClass: 'badge-in-progress',
  },
  WAITING_DOCUMENTS: {
    label: 'Waiting Docs',
    icon: '📄',
    colorClass: 'status-waiting-docs',
    badgeClass: 'badge-waiting-docs',
  },
  ON_HOLD: {
    label: 'On Hold',
    icon: '⏸️',
    colorClass: 'status-on-hold',
    badgeClass: 'badge-on-hold',
  },
  UNDER_REVIEW: {
    label: 'Under Review',
    icon: '🔍',
    colorClass: 'status-under-review',
    badgeClass: 'badge-under-review',
  },
  COMPLETED: {
    label: 'Completed',
    icon: '✅',
    colorClass: 'status-completed',
    badgeClass: 'badge-completed',
  },
  CANCELLED: {
    label: 'Cancelled',
    icon: '✕',
    colorClass: 'status-cancelled',
    badgeClass: 'badge-neutral',
  },
}

function getStatusMeta(statusKey) {
  return STATUS_CONFIG[statusKey] || {
    label: statusKey || 'Unknown',
    icon: '•',
    colorClass: 'status-default',
    badgeClass: 'badge-neutral',
  }
}

// ---------------------------------------------------------------
// COMPUTED PROPERTIES
// ---------------------------------------------------------------
const uniqueStaffList = computed(() => {
  const set = new Set()
  staffList.value.forEach((s) => {
    if (s.name && s.name.trim()) {
      set.add(s.name.trim())
    }
  })
  tasks.value.forEach((t) => {
    if (t.assigned_staff && t.assigned_staff.trim()) {
      set.add(t.assigned_staff.trim())
    }
  })
  return Array.from(set).sort()
})

const filteredTasks = computed(() => {
  let result = [...tasks.value]

  // Filter: Search Query
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    result = result.filter((t) => {
      const clientName = t.client?.business_name?.toLowerCase() || ''
      const contactName = t.client?.contact_name?.toLowerCase() || ''
      const matter = t.matter?.toLowerCase() || ''
      const staff = t.assigned_staff?.toLowerCase() || ''
      const remarks = t.remarks?.toLowerCase() || ''
      const docs = t.documents?.toLowerCase() || ''
      return (
        matter.includes(q) ||
        clientName.includes(q) ||
        contactName.includes(q) ||
        staff.includes(q) ||
        remarks.includes(q) ||
        docs.includes(q)
      )
    })
  }

  // Filter: Status
  if (statusFilter.value !== 'ALL') {
    result = result.filter((t) => t.status === statusFilter.value)
  }

  // Filter: Staff
  if (staffFilter.value !== 'ALL') {
    result = result.filter((t) => t.assigned_staff === staffFilter.value)
  }

  // Filter: Overdue Only
  if (overdueOnly.value) {
    result = result.filter((t) => isOverdue(t))
  }

  // Sorting
  result.sort((a, b) => {
    let comparison = 0
    if (sortBy.value === 'due_date') {
      const valA = a.due_date || '9999-99-99'
      const valB = b.due_date || '9999-99-99'
      comparison = valA.localeCompare(valB)
    } else if (sortBy.value === 'date_assigned') {
      const valA = a.date_assigned || ''
      const valB = b.date_assigned || ''
      comparison = valB.localeCompare(valA)
    } else if (sortBy.value === 'matter') {
      comparison = (a.matter || '').localeCompare(b.matter || '')
    } else if (sortBy.value === 'client') {
      const nameA = a.client?.business_name || ''
      const nameB = b.client?.business_name || ''
      comparison = nameA.localeCompare(nameB)
    }

    return sortOrder.value === 'asc' ? comparison : -comparison
  })

  return result
})

const activeFilterCount = computed(() => {
  let count = 0
  if (searchQuery.value.trim()) count++
  if (statusFilter.value !== 'ALL') count++
  if (staffFilter.value !== 'ALL') count++
  if (overdueOnly.value) count++
  return count
})

// ---------------------------------------------------------------
// API INTEGRATION METHODS
// ---------------------------------------------------------------
async function loadData() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [tasksRes, metricsRes, clientsRes, staffRes] = await Promise.all([
      api.getTasks(),
      api.getTaskMetrics(),
      api.getClients({ is_active: true }),
      api.getStaff({ is_active: true }),
    ])

    if (tasksRes.error) throw new Error(tasksRes.error.message)
    if (tasksRes.data) tasks.value = tasksRes.data

    if (metricsRes.data) metrics.value = metricsRes.data
    if (clientsRes.data) clients.value = clientsRes.data
    if (staffRes?.data) staffList.value = staffRes.data
  } catch (err) {
    errorMsg.value = err.message || 'Failed to load task data. Please check connection.'
  } finally {
    loading.value = false
  }
}

async function refreshTasksOnly() {
  const [tasksRes, metricsRes] = await Promise.all([
    api.getTasks(),
    api.getTaskMetrics(),
  ])
  if (tasksRes.data) tasks.value = tasksRes.data
  if (metricsRes.data) metrics.value = metricsRes.data
}

function handleSearchInput() {
  clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    // Live client-side filter is instant
  }, 250)
}

function clearFilters() {
  searchQuery.value = ''
  statusFilter.value = 'ALL'
  staffFilter.value = 'ALL'
  overdueOnly.value = false
}

function toggleSort(field) {
  if (sortBy.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = field
    sortOrder.value = 'asc'
  }
}

// ---------------------------------------------------------------
// MODAL / DRAWER MANAGEMENT
// ---------------------------------------------------------------
function openCreateDrawer() {
  isEditing.value = false
  Object.assign(formData, defaultFormData())
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
  isDrawerOpen.value = true
}

function openEditDrawer(task) {
  isEditing.value = true
  Object.assign(formData, {
    id: task.id,
    client_id: task.client_id,
    matter: task.matter,
    assigned_staff: task.assigned_staff || '',
    date_assigned: task.date_assigned || getTodayString(),
    due_date: task.due_date || '',
    next_followup_date: task.next_followup_date || '',
    status: task.status || 'PENDING',
    remarks: task.remarks || '',
    documents: task.documents || '',
  })
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
  isDrawerOpen.value = true
}

function closeDrawer() {
  if (saving.value) return
  isDrawerOpen.value = false
}

function validateForm() {
  let valid = true
  Object.keys(formErrors).forEach((k) => delete formErrors[k])

  if (!formData.matter.trim()) {
    formErrors.matter = 'Matter title or description is required.'
    valid = false
  }
  if (!formData.client_id) {
    formErrors.client_id = 'Please select an associated client.'
    valid = false
  }
  if (formData.date_assigned && formData.due_date) {
    if (formData.due_date < formData.date_assigned) {
      formErrors.due_date = 'Due date cannot be before date assigned.'
      valid = false
    }
  }
  return valid
}

async function handleSaveTask() {
  if (!validateForm()) return

  saving.value = true
  try {
    const payload = {
      client_id: Number(formData.client_id),
      matter: formData.matter.trim(),
      assigned_staff: formData.assigned_staff.trim() || null,
      date_assigned: formData.date_assigned || null,
      due_date: formData.due_date || null,
      next_followup_date: formData.next_followup_date || null,
      status: formData.status,
      remarks: formData.remarks.trim() || null,
      documents: formData.documents.trim() || null,
    }

    if (isEditing.value) {
      const res = await api.updateTask(formData.id, payload)
      if (res.error) throw new Error(res.error.message)
      showToast(`Matter "${formData.matter}" updated successfully!`)
    } else {
      const res = await api.createTask(payload)
      if (res.error) throw new Error(res.error.message)
      showToast(`New matter "${formData.matter}" created!`)
    }

    closeDrawer()
    await refreshTasksOnly()
  } catch (err) {
    formErrors.general = err.message || 'Failed to save matter. Please try again.'
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------
// QUICK STATUS CHANGE DIRECTLY FROM TABLE
// ---------------------------------------------------------------
async function handleQuickStatusChange(task, newStatus) {
  if (task.status === newStatus) return
  const oldStatus = task.status
  task.status = newStatus // Optimistic update

  const res = await api.updateTaskStatus(task.id, newStatus)
  if (res.error) {
    task.status = oldStatus // Revert
    showToast(res.error.message || 'Failed to update status', 'error')
  } else {
    showToast(`Status updated to ${getStatusMeta(newStatus).label}`)
    const metricsRes = await api.getTaskMetrics()
    if (metricsRes.data) metrics.value = metricsRes.data
  }
}

// ---------------------------------------------------------------
// WHATSAPP REMINDER
// ---------------------------------------------------------------
function openReminderModal(task) {
  activeReminderTask.value = task
  customReminderMessage.value = ''
  reminderResult.value = null
  isReminderModalOpen.value = true
}

function closeReminderModal() {
  if (sendingReminder.value) return
  isReminderModalOpen.value = false
  activeReminderTask.value = null
}

async function handleSendReminder() {
  if (!activeReminderTask.value) return
  sendingReminder.value = true
  reminderResult.value = null

  try {
    const payload = customReminderMessage.value.trim()
      ? { custom_message: customReminderMessage.value.trim() }
      : {}

    const res = await api.sendTaskReminder(activeReminderTask.value.id, payload)
    if (res.error) throw new Error(res.error.message)

    reminderResult.value = res.data
    showToast(
      `WhatsApp reminder sent to ${activeReminderTask.value.client?.contact_name || 'Client'}!`
    )
  } catch (err) {
    showToast(err.message || 'Failed to send WhatsApp reminder', 'error')
  } finally {
    sendingReminder.value = false
  }
}

// ---------------------------------------------------------------
// DELETE HANDLING
// ---------------------------------------------------------------
function confirmDelete(task) {
  taskToDelete.value = task
  isDeleteModalOpen.value = true
}

function closeDeleteModal() {
  if (deleting.value) return
  isDeleteModalOpen.value = false
  taskToDelete.value = null
}

async function executeDelete() {
  if (!taskToDelete.value) return
  deleting.value = true
  try {
    const res = await api.deleteTask(taskToDelete.value.id)
    if (res.error) throw new Error(res.error.message)

    showToast(`Matter "${taskToDelete.value.matter}" deleted successfully.`)
    closeDeleteModal()
    await refreshTasksOnly()
  } catch (err) {
    showToast(err.message || 'Failed to delete matter', 'error')
  } finally {
    deleting.value = false
  }
}

// Quick filter helper from metric cards
function applyMetricFilter(statusKey) {
  if (statusKey === 'OVERDUE') {
    overdueOnly.value = true
    statusFilter.value = 'ALL'
  } else {
    overdueOnly.value = false
    statusFilter.value = statusKey
  }
}

// Keyboard shortcut: close drawer on Esc
function handleKeyDown(e) {
  if (e.key === 'Escape') {
    if (isDrawerOpen.value) closeDrawer()
    if (isReminderModalOpen.value) closeReminderModal()
    if (isDeleteModalOpen.value) closeDeleteModal()
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <div class="task-manager-view">
    <!-- ============================= TOAST NOTIFICATION ============================= -->
    <Transition name="toast-fade">
      <div v-if="toast.show" class="floating-toast" :class="`toast-${toast.type}`">
        <span class="toast-icon">{{ toast.type === 'success' ? '✅' : '⚠️' }}</span>
        <span>{{ toast.message }}</span>
      </div>
    </Transition>

    <!-- ============================= PAGE HEADER ============================= -->
    <div class="header-card card">
      <div class="header-main">
        <div>
          <div class="breadcrumb">Compliance & Workflow</div>
          <h1 class="header-title">Matter & Task Management</h1>
          <p class="header-subtitle">
            Track filing deadlines, assign team tasks, monitor overdue deliverables, and send automated WhatsApp reminders.
          </p>
        </div>

        <div class="header-actions">
          <button class="btn btn-outline" :disabled="loading" @click="loadData">
            <span class="refresh-icon" :class="{ rotating: loading }">🔄</span>
            Refresh
          </button>
          <button class="btn btn-primary btn-cta" @click="openCreateDrawer">
            <span class="btn-icon">＋</span> New Matter
          </button>
        </div>
      </div>

      <!-- ============================= METRIC STATUS CARDS ============================= -->
      <div v-if="metrics" class="metrics-grid">
        <div
          class="metric-pill"
          :class="{ active: statusFilter === 'ALL' && !overdueOnly }"
          @click="clearFilters"
        >
          <div class="metric-num">{{ metrics.total_tasks }}</div>
          <div class="metric-lbl">All Matters</div>
        </div>

        <div
          class="metric-pill metric-in-progress"
          :class="{ active: statusFilter === 'IN_PROGRESS' }"
          @click="applyMetricFilter('IN_PROGRESS')"
        >
          <div class="metric-num">{{ metrics.in_progress_tasks }}</div>
          <div class="metric-lbl">🔄 In Progress</div>
        </div>

        <div
          class="metric-pill metric-pending"
          :class="{ active: statusFilter === 'PENDING' }"
          @click="applyMetricFilter('PENDING')"
        >
          <div class="metric-num">{{ metrics.pending_tasks }}</div>
          <div class="metric-lbl">⏳ Pending</div>
        </div>

        <div
          class="metric-pill metric-waiting"
          :class="{ active: statusFilter === 'WAITING_DOCUMENTS' }"
          @click="applyMetricFilter('WAITING_DOCUMENTS')"
        >
          <div class="metric-num">{{ metrics.waiting_documents_tasks }}</div>
          <div class="metric-lbl">📄 Waiting Docs</div>
        </div>

        <div
          class="metric-pill metric-overdue"
          :class="{ active: overdueOnly }"
          @click="applyMetricFilter('OVERDUE')"
        >
          <div class="metric-num pulse-alert">{{ metrics.overdue_tasks }}</div>
          <div class="metric-lbl">⚠️ Overdue</div>
        </div>

        <div
          class="metric-pill metric-completed"
          :class="{ active: statusFilter === 'COMPLETED' }"
          @click="applyMetricFilter('COMPLETED')"
        >
          <div class="metric-num">{{ metrics.completed_tasks }}</div>
          <div class="metric-lbl">✅ Completed</div>
        </div>
      </div>
    </div>

    <!-- ============================= ERROR BANNER ============================= -->
    <div v-if="errorMsg" class="alert alert-error">
      <div class="alert-content">
        <span>⚠️ <strong>Error:</strong> {{ errorMsg }}</span>
        <button class="btn btn-outline btn-sm" @click="loadData">Try Again</button>
      </div>
    </div>

    <!-- ============================= CONTROLS & FILTER BAR ============================= -->
    <div class="card filter-bar-card">
      <div class="search-input-wrapper">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search matters, clients, staff, remarks..."
          class="search-input"
          @input="handleSearchInput"
        />
        <button
          v-if="searchQuery"
          class="clear-search-btn"
          title="Clear search"
          @click="searchQuery = ''"
        >
          ✕
        </button>
      </div>

      <div class="filter-controls">
        <div class="filter-group">
          <label class="filter-label">Status:</label>
          <select v-model="statusFilter" class="filter-select">
            <option value="ALL">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="WAITING_DOCUMENTS">Waiting Documents</option>
            <option value="ON_HOLD">On Hold</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>

        <div v-if="uniqueStaffList.length > 0" class="filter-group">
          <label class="filter-label">Staff:</label>
          <select v-model="staffFilter" class="filter-select">
            <option value="ALL">All Staff</option>
            <option v-for="staff in uniqueStaffList" :key="staff" :value="staff">
              {{ staff }}
            </option>
          </select>
        </div>

        <button
          class="btn btn-overdue-toggle"
          :class="{ active: overdueOnly }"
          @click="overdueOnly = !overdueOnly"
        >
          <span class="overdue-dot"></span>
          Overdue Only
        </button>

        <button
          v-if="activeFilterCount > 0"
          class="btn btn-clear-filters"
          @click="clearFilters"
        >
          Reset ({{ activeFilterCount }})
        </button>
      </div>
    </div>

    <!-- ============================= DATA TABLE CARD ============================= -->
    <div class="card table-card">
      <div class="table-card-header">
        <div class="results-count">
          Showing <strong>{{ filteredTasks.length }}</strong> matter{{
            filteredTasks.length === 1 ? '' : 's'
          }}
          <span v-if="activeFilterCount > 0" class="filter-applied-badge">Filtered</span>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="loading-container">
        <div class="loading-spinner"></div>
        <p>Loading compliance matters...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredTasks.length === 0" class="empty-container">
        <div class="empty-icon">📁</div>
        <h3>No compliance matters found</h3>
        <p v-if="activeFilterCount > 0">
          No records match your active search or filters. Try adjusting them.
        </p>
        <p v-else>Get started by creating your first client compliance matter.</p>
        <div class="empty-actions">
          <button v-if="activeFilterCount > 0" class="btn btn-outline" @click="clearFilters">
            Clear All Filters
          </button>
          <button class="btn btn-primary" @click="openCreateDrawer">
            ＋ Create First Matter
          </button>
        </div>
      </div>

      <!-- Responsive Data Table -->
      <div v-else class="table-responsive">
        <table class="matters-table">
          <thead>
            <tr>
              <!-- 1. Matter -->
              <th class="th-sortable" @click="toggleSort('matter')">
                <div class="th-content">
                  <span>Matter / Description</span>
                  <span class="sort-arrow" v-if="sortBy === 'matter'">{{
                    sortOrder === 'asc' ? '▲' : '▼'
                  }}</span>
                </div>
              </th>

              <!-- 2. Client -->
              <th class="th-sortable" @click="toggleSort('client')">
                <div class="th-content">
                  <span>Client / Entity</span>
                  <span class="sort-arrow" v-if="sortBy === 'client'">{{
                    sortOrder === 'asc' ? '▲' : '▼'
                  }}</span>
                </div>
              </th>

              <!-- 3. Assigned Staff -->
              <th>Assigned Staff</th>

              <!-- 4. Date Assigned -->
              <th class="th-sortable" @click="toggleSort('date_assigned')">
                <div class="th-content">
                  <span>Assigned Date</span>
                  <span class="sort-arrow" v-if="sortBy === 'date_assigned'">{{
                    sortOrder === 'asc' ? '▲' : '▼'
                  }}</span>
                </div>
              </th>

              <!-- 5. Due Date (With conditional cue) -->
              <th class="th-sortable" @click="toggleSort('due_date')">
                <div class="th-content">
                  <span>Due Date</span>
                  <span class="sort-arrow" v-if="sortBy === 'due_date'">{{
                    sortOrder === 'asc' ? '▲' : '▼'
                  }}</span>
                </div>
              </th>

              <!-- 6. Next Follow-up -->
              <th>Next Follow-up</th>

              <!-- 7. Status -->
              <th>Status</th>

              <!-- 8. Remarks & Documents -->
              <th>Remarks & Docs</th>

              <!-- Actions -->
              <th class="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in filteredTasks"
              :key="task.id"
              :class="{
                'row-overdue': isOverdue(task),
                'row-due-today': isDueToday(task),
                'row-completed': task.status === 'COMPLETED',
              }"
            >
              <!-- 1. Matter -->
              <td class="td-matter">
                <div class="matter-title">{{ task.matter }}</div>
                <div v-if="task.documents" class="matter-doc-pill">
                  📎 {{ task.documents }}
                </div>
              </td>

              <!-- 2. Client -->
              <td class="td-client">
                <div v-if="task.client" class="client-meta">
                  <div class="client-name">{{ task.client.business_name }}</div>
                  <div class="client-contact">
                    <span>👤 {{ task.client.contact_name }}</span>
                    <span v-if="task.client.mobile_number" class="client-phone">
                      · 📱 +{{ task.client.mobile_number }}
                    </span>
                  </div>
                </div>
                <div v-else class="client-unknown">—</div>
              </td>

              <!-- 3. Assigned Staff -->
              <td class="td-staff">
                <div v-if="task.assigned_staff" class="staff-badge">
                  <span class="staff-avatar">{{ task.assigned_staff.charAt(0) }}</span>
                  <span class="staff-name">{{ task.assigned_staff }}</span>
                </div>
                <span v-else class="text-muted-dash">Unassigned</span>
              </td>

              <!-- 4. Date Assigned -->
              <td class="td-date">
                {{ formatDate(task.date_assigned) }}
              </td>

              <!-- 5. Due Date (VISUAL STATUS CUES: Conditional Highlight for Overdue items) -->
              <td class="td-due-date">
                <div v-if="isOverdue(task)" class="overdue-cue">
                  <span class="overdue-badge">⚠️ Overdue</span>
                  <span class="overdue-text">
                    {{ formatDate(task.due_date) }}
                    <small>({{ daysOverdue(task) }}d late)</small>
                  </span>
                </div>
                <div v-else-if="isDueToday(task)" class="due-today-cue">
                  <span class="due-today-badge">⏰ Today</span>
                  <span class="due-today-text">{{ formatDate(task.due_date) }}</span>
                </div>
                <div v-else-if="task.due_date" class="normal-due-date">
                  📅 {{ formatDate(task.due_date) }}
                </div>
                <span v-else class="text-muted-dash">—</span>
              </td>

              <!-- 6. Next Follow-up -->
              <td class="td-followup">
                <div v-if="task.next_followup_date" class="followup-badge">
                  {{ formatDate(task.next_followup_date) }}
                </div>
                <span v-else class="text-muted-dash">—</span>
              </td>

              <!-- 7. Status (Color-Coded Status Badge with Quick Toggle) -->
              <td class="td-status">
                <div class="status-cell-wrapper">
                  <span
                    class="status-pill"
                    :class="getStatusMeta(task.status).badgeClass"
                  >
                    <span class="status-icon">{{ getStatusMeta(task.status).icon }}</span>
                    <span>{{ getStatusMeta(task.status).label }}</span>
                  </span>

                  <!-- Quick Status Dropdown -->
                  <select
                    :value="task.status"
                    class="quick-status-select"
                    title="Change status"
                    @change="handleQuickStatusChange(task, $event.target.value)"
                  >
                    <option value="PENDING">⏳ Pending</option>
                    <option value="IN_PROGRESS">🔄 In Progress</option>
                    <option value="WAITING_DOCUMENTS">📄 Waiting Docs</option>
                    <option value="ON_HOLD">⏸️ On Hold</option>
                    <option value="UNDER_REVIEW">🔍 Under Review</option>
                    <option value="COMPLETED">✅ Completed</option>
                    <option value="CANCELLED">✕ Cancelled</option>
                  </select>
                </div>
              </td>

              <!-- 8. Remarks & Documents -->
              <td class="td-remarks">
                <div v-if="task.remarks" class="remarks-text" :title="task.remarks">
                  {{ task.remarks }}
                </div>
                <span v-else class="text-muted-dash">—</span>
              </td>

              <!-- Actions -->
              <td class="td-actions">
                <div class="action-buttons-wrapper">
                  <!-- WhatsApp Reminder -->
                  <button
                    class="btn-action btn-action-wa"
                    title="Send WhatsApp Reminder"
                    @click="openReminderModal(task)"
                  >
                    💬
                  </button>

                  <!-- Edit -->
                  <button
                    class="btn-action btn-action-edit"
                    title="Edit Matter"
                    @click="openEditDrawer(task)"
                  >
                    ✏️
                  </button>

                  <!-- Delete -->
                  <button
                    class="btn-action btn-action-delete"
                    title="Delete Matter"
                    @click="confirmDelete(task)"
                  >
                    🗑️
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ============================= INTERACTIVE MODAL / DRAWER ============================= -->
    <div
      v-if="isDrawerOpen"
      class="drawer-overlay"
      @click.self="closeDrawer"
    >
      <div class="drawer-container">
        <div class="drawer-header">
          <div>
            <div class="drawer-subtitle">
              {{ isEditing ? 'Edit Existing Record' : 'Add Compliance Deliverable' }}
            </div>
            <h2 class="drawer-title">
              {{ isEditing ? 'Edit Matter Entry' : 'Create New Matter' }}
            </h2>
          </div>
          <button class="drawer-close-btn" title="Close" @click="closeDrawer">✕</button>
        </div>

        <form class="drawer-body" @submit.prevent="handleSaveTask">
          <!-- General Form Error Banner -->
          <div v-if="formErrors.general" class="alert alert-error">
            {{ formErrors.general }}
          </div>

          <!-- Matter Description -->
          <div class="form-group">
            <label>
              Matter / Work Description <span class="required">*</span>
            </label>
            <input
              v-model="formData.matter"
              type="text"
              placeholder="e.g. GSTR-3B Filing, ITR Audit Form 3CA/3CD, TDS 26Q"
              :class="{ 'input-invalid': formErrors.matter }"
            />
            <span v-if="formErrors.matter" class="field-error">{{ formErrors.matter }}</span>
          </div>

          <!-- Client Selection -->
          <div class="form-group">
            <label>
              Associated Client <span class="required">*</span>
            </label>
            <select
              v-model="formData.client_id"
              :class="{ 'input-invalid': formErrors.client_id }"
            >
              <option value="" disabled>-- Select a Client --</option>
              <option v-for="c in clients" :key="c.id" :value="c.id">
                {{ c.business_name }} ({{ c.contact_name }} - {{ c.mobile_number }})
              </option>
            </select>
            <span v-if="formErrors.client_id" class="field-error">{{
              formErrors.client_id
            }}</span>
          </div>

          <!-- Staff Assignment & Status in Two Columns -->
          <div class="form-row">
            <div class="form-group">
              <label>Assigned Staff</label>
              <input
                v-model="formData.assigned_staff"
                type="text"
                placeholder="e.g. Rahul Sharma, Pooja Verma"
                list="staff-suggestions"
              />
              <datalist id="staff-suggestions">
                <option v-for="staffName in uniqueStaffList" :key="staffName" :value="staffName"></option>
              </datalist>
            </div>

            <div class="form-group">
              <label>Current Status</label>
              <select v-model="formData.status">
                <option value="PENDING">⏳ Pending</option>
                <option value="IN_PROGRESS">🔄 In Progress</option>
                <option value="WAITING_DOCUMENTS">📄 Waiting Documents</option>
                <option value="ON_HOLD">⏸️ On Hold</option>
                <option value="UNDER_REVIEW">🔍 Under Review</option>
                <option value="COMPLETED">✅ Completed</option>
                <option value="CANCELLED">✕ Cancelled</option>
              </select>
            </div>
          </div>

          <!-- Dates in 3 Columns: Assigned Date, Due Date, Next Follow-up -->
          <div class="form-row form-row-3">
            <div class="form-group">
              <label>Date Assigned</label>
              <input v-model="formData.date_assigned" type="date" />
            </div>

            <div class="form-group">
              <label>Due Date</label>
              <input
                v-model="formData.due_date"
                type="date"
                :class="{ 'input-invalid': formErrors.due_date }"
              />
              <span v-if="formErrors.due_date" class="field-error">{{
                formErrors.due_date
              }}</span>
            </div>

            <div class="form-group">
              <label>Next Follow-up</label>
              <input v-model="formData.next_followup_date" type="date" />
            </div>
          </div>

          <!-- Required Documents -->
          <div class="form-group">
            <label>Pending / Required Documents</label>
            <input
              v-model="formData.documents"
              type="text"
              placeholder="e.g. Bank Statement (Aug), Sales Ledger, Form 26AS"
            />
            <small class="field-hint">
              These will be automatically included when triggering WhatsApp document reminders.
            </small>
          </div>

          <!-- Internal Remarks / Notes -->
          <div class="form-group">
            <label>Internal Remarks / Notes</label>
            <textarea
              v-model="formData.remarks"
              rows="3"
              placeholder="Add status notes, client communication notes, or pending queries..."
            ></textarea>
          </div>

          <!-- Drawer Actions -->
          <div class="drawer-footer">
            <button
              type="button"
              class="btn btn-outline"
              :disabled="saving"
              @click="closeDrawer"
            >
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="btn-spinner"></span>
              <span>{{ saving ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Matter' }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ============================= WHATSAPP REMINDER MODAL ============================= -->
    <div
      v-if="isReminderModalOpen"
      class="modal-overlay"
      @click.self="closeReminderModal"
    >
      <div class="modal-box reminder-modal">
        <div class="modal-header">
          <div class="reminder-header-title">
            <span class="modal-icon-wa">💬</span>
            <h3>Send WhatsApp Compliance Reminder</h3>
          </div>
          <button class="modal-close" @click="closeReminderModal">✕</button>
        </div>

        <div v-if="activeReminderTask" class="reminder-body">
          <div class="client-reminder-card">
            <div class="reminder-recipient">
              <strong>Recipient:</strong> {{ activeReminderTask.client?.contact_name }} ({{
                activeReminderTask.client?.business_name
              }})
            </div>
            <div class="reminder-phone">
              📱 +{{ activeReminderTask.client?.mobile_number }}
            </div>
            <div class="reminder-meta">
              <span><strong>Matter:</strong> {{ activeReminderTask.matter }}</span>
              <span><strong>Due Date:</strong> {{ formatDate(activeReminderTask.due_date) }}</span>
            </div>
          </div>

          <!-- Result banner if sent -->
          <div v-if="reminderResult" class="alert alert-success">
            <div>
              <strong>WhatsApp Message Processed:</strong>
              <div class="result-detail">
                Status: {{ reminderResult.status }}
                <span v-if="reminderResult.simulated">(Simulated Mode)</span>
              </div>
            </div>
          </div>

          <div class="form-group">
            <label>Custom Note / Additional Instructions (Optional):</label>
            <textarea
              v-model="customReminderMessage"
              rows="4"
              placeholder="Leave blank to send standard automated template including due date & document checklist..."
            ></textarea>
            <small class="field-hint">
              If left blank, Gateway Solutions automated compliance reminder template will be sent.
            </small>
          </div>
        </div>

        <div class="modal-footer">
          <button
            class="btn btn-outline"
            :disabled="sendingReminder"
            @click="closeReminderModal"
          >
            {{ reminderResult ? 'Close' : 'Cancel' }}
          </button>
          <button
            class="btn btn-whatsapp"
            :disabled="sendingReminder || reminderResult !== null"
            @click="handleSendReminder"
          >
            <span v-if="sendingReminder" class="btn-spinner"></span>
            <span>{{ sendingReminder ? 'Sending...' : 'Send WhatsApp Message' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ============================= DELETE CONFIRMATION MODAL ============================= -->
    <div
      v-if="isDeleteModalOpen"
      class="modal-overlay"
      @click.self="closeDeleteModal"
    >
      <div class="modal-box delete-confirm-modal">
        <div class="modal-header">
          <h3 class="delete-header-title">⚠️ Confirm Delete</h3>
          <button class="modal-close" @click="closeDeleteModal">✕</button>
        </div>

        <div class="delete-body">
          <p>
            Are you sure you want to delete matter:
            <strong>"{{ taskToDelete?.matter }}"</strong>?
          </p>
          <p class="delete-warning-text">
            This action cannot be undone. Associated reminder logs will be preserved.
          </p>
        </div>

        <div class="modal-footer">
          <button class="btn btn-outline" :disabled="deleting" @click="closeDeleteModal">
            Cancel
          </button>
          <button class="btn btn-danger" :disabled="deleting" @click="executeDelete">
            <span v-if="deleting" class="btn-spinner"></span>
            <span>{{ deleting ? 'Deleting...' : 'Delete Matter' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* =================================================================
   ROOT & LAYOUT
   ================================================================= */
.task-manager-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
}

/* =================================================================
   HEADER CARD & METRICS
   ================================================================= */
.header-card {
  padding: 24px;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.breadcrumb {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--primary);
  font-weight: 700;
  margin-bottom: 4px;
}

.header-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 6px 0;
}

.header-subtitle {
  color: var(--text-muted);
  font-size: 14px;
  margin: 0;
  max-width: 650px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-cta {
  box-shadow: 0 4px 12px rgba(7, 94, 84, 0.25);
  font-weight: 600;
}

.refresh-icon.rotating {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.metric-pill {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  text-align: left;
}

.metric-pill:hover {
  transform: translateY(-2px);
  border-color: var(--primary-light);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.metric-pill.active {
  border-color: var(--primary);
  background: rgba(7, 94, 84, 0.08);
  font-weight: 600;
}

.metric-num {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.2;
}

.metric-lbl {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.metric-in-progress .metric-num {
  color: #0284c7;
}
.metric-pending .metric-num {
  color: #d97706;
}
.metric-waiting .metric-num {
  color: #ea580c;
}
.metric-overdue .metric-num {
  color: var(--danger);
}
.metric-completed .metric-num {
  color: var(--success);
}

.pulse-alert {
  display: inline-block;
}

/* =================================================================
   FILTER & SEARCH BAR
   ================================================================= */
.filter-bar-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  flex-wrap: wrap;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  position: relative;
  flex: 1;
  min-width: 260px;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 14px;
  color: var(--text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 9px 34px 9px 36px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--surface);
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
}

.search-input:focus {
  border-color: var(--primary-light);
  box-shadow: 0 0 0 3px rgba(18, 140, 126, 0.15);
}

.clear-search-btn {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 12px;
}

.filter-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
}

.filter-select {
  padding: 7px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  font-size: 13px;
  background: var(--surface);
  color: var(--text);
  outline: none;
  cursor: pointer;
}

.btn-overdue-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  font-size: 13px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-muted);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.overdue-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--danger);
  opacity: 0.4;
}

.btn-overdue-toggle.active {
  background: #fef2f2;
  border-color: #fca5a5;
  color: var(--danger);
  font-weight: 600;
}

.btn-overdue-toggle.active .overdue-dot {
  opacity: 1;
  box-shadow: 0 0 6px var(--danger);
}

.btn-clear-filters {
  background: none;
  border: none;
  color: var(--primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 8px;
}

.btn-clear-filters:hover {
  text-decoration: underline;
}

/* =================================================================
   TABLE CARD & STYLING
   ================================================================= */
.table-card {
  padding: 0;
  overflow: hidden;
}

.table-card-header {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.results-count {
  font-size: 13px;
  color: var(--text-muted);
}

.results-count strong {
  color: var(--text);
}

.filter-applied-badge {
  display: inline-block;
  margin-left: 8px;
  font-size: 11px;
  padding: 2px 6px;
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 4px;
}

.table-responsive {
  width: 100%;
  overflow-x: auto;
}

.matters-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}

.matters-table th {
  padding: 12px 14px;
  font-weight: 600;
  font-size: 12.5px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
  background: #f8fafc;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.th-sortable {
  cursor: pointer;
  user-select: none;
}

.th-sortable:hover {
  background: #f1f5f9;
  color: var(--primary);
}

.th-content {
  display: flex;
  align-items: center;
  gap: 4px;
}

.sort-arrow {
  font-size: 10px;
  color: var(--primary);
}

.th-actions {
  text-align: right;
}

.matters-table td {
  padding: 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

/* Row states */
.matters-table tbody tr {
  transition: background-color 0.15s;
}

.matters-table tbody tr:hover {
  background: #f8fafc;
}

/* CONDITIONAL HIGHLIGHT: Overdue row style */
.row-overdue {
  background: #fffafa !important;
  border-left: 4px solid var(--danger);
}

.row-overdue:hover {
  background: #fff1f2 !important;
}

.row-due-today {
  border-left: 4px solid #f59e0b;
}

.row-completed {
  opacity: 0.85;
}

/* Column 1: Matter */
.td-matter {
  min-width: 200px;
  max-width: 280px;
}

.matter-title {
  font-weight: 600;
  color: var(--text);
  line-height: 1.35;
}

.matter-doc-pill {
  display: inline-block;
  margin-top: 4px;
  font-size: 11px;
  color: #0369a1;
  background: #e0f2fe;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 240px;
}

/* Column 2: Client */
.td-client {
  min-width: 180px;
}

.client-name {
  font-weight: 600;
  color: var(--text);
}

.client-contact {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.client-phone {
  font-family: monospace;
}

/* Column 3: Staff */
.td-staff {
  white-space: nowrap;
}

.staff-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 20px;
  background: #f1f5f9;
  font-size: 12px;
}

.staff-avatar {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: bold;
}

.staff-name {
  color: var(--text);
}

/* Column 4 & 6: Dates */
.td-date,
.td-followup {
  white-space: nowrap;
  color: var(--text);
  font-size: 13px;
}

.followup-badge {
  display: inline-block;
  background: #f1f5f9;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
}

/* Column 5: Due Date (Visual Status Cue) */
.td-due-date {
  min-width: 150px;
  white-space: nowrap;
}

.overdue-cue {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.overdue-badge {
  display: inline-block;
  align-self: flex-start;
  font-size: 11px;
  font-weight: 700;
  background: #fee2e2;
  color: var(--danger);
  padding: 1px 6px;
  border-radius: 4px;
}

.overdue-text {
  color: var(--danger);
  font-weight: 600;
}

.overdue-text small {
  font-weight: normal;
  font-size: 11px;
}

.due-today-cue {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.due-today-badge {
  display: inline-block;
  align-self: flex-start;
  font-size: 11px;
  font-weight: 700;
  background: #fef3c7;
  color: #b45309;
  padding: 1px 6px;
  border-radius: 4px;
}

.due-today-text {
  color: #b45309;
  font-weight: 600;
}

.normal-due-date {
  color: var(--text);
}

/* Column 7: Status Badges & Quick Dropdown */
.td-status {
  white-space: nowrap;
}

.status-cell-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  position: relative;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-pending {
  background: #fef3c7;
  color: #b45309;
}
.badge-in-progress {
  background: #e0f2fe;
  color: #0369a1;
}
.badge-waiting-docs {
  background: #ffedd5;
  color: #c2410c;
}
.badge-on-hold {
  background: #f3e8ff;
  color: #7e22ce;
}
.badge-under-review {
  background: #e0e7ff;
  color: #4338ca;
}
.badge-completed {
  background: #dcfce7;
  color: #15803d;
}

.quick-status-select {
  opacity: 0.15;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  cursor: pointer;
  transition: opacity 0.15s;
}

.matters-table tbody tr:hover .quick-status-select,
.quick-status-select:focus {
  opacity: 1;
}

/* Column 8: Remarks */
.td-remarks {
  max-width: 220px;
}

.remarks-text {
  font-size: 12.5px;
  color: var(--text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.35;
}

/* Actions Column */
.td-actions {
  text-align: right;
  white-space: nowrap;
}

.action-buttons-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-action {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.15s;
}

.btn-action:hover {
  transform: scale(1.08);
}

.btn-action-wa {
  background: #f0fdf4;
  border-color: #bbf7d0;
}
.btn-action-wa:hover {
  background: #25d366;
  border-color: #20ba5a;
}

.btn-action-edit:hover {
  background: #f0fdfa;
  border-color: var(--primary);
}

.btn-action-delete:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}

.text-muted-dash {
  color: var(--text-muted);
  opacity: 0.6;
}

/* Loading & Empty States */
.loading-container,
.empty-container {
  padding: 60px 20px;
  text-align: center;
  color: var(--text-muted);
}

.loading-spinner {
  width: 36px;
  height: 36px;
  margin: 0 auto 16px auto;
  border: 3px solid rgba(7, 94, 84, 0.2);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.7;
}

.empty-container h3 {
  font-size: 18px;
  color: var(--text);
  margin-bottom: 6px;
}

.empty-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 18px;
}

/* =================================================================
   INTERACTIVE MODAL / DRAWER
   ================================================================= */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: flex-end;
  z-index: 200;
  animation: fadeIn 0.2s ease-out;
}

.drawer-container {
  background: var(--surface);
  color: var(--text);
  width: 100%;
  max-width: 540px;
  height: 100vh;
  box-shadow: -10px 0 25px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  animation: slideInRight 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.drawer-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface);
}

.drawer-subtitle {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--primary);
  font-weight: 700;
}

.drawer-title {
  font-size: 20px;
  font-weight: 700;
  margin: 2px 0 0 0;
}

.drawer-close-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
}

.drawer-close-btn:hover {
  color: var(--text);
}

.drawer-body {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.form-row-3 {
  grid-template-columns: 1fr 1fr 1fr;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 0;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.required {
  color: var(--danger);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--surface);
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: var(--primary-light);
  box-shadow: 0 0 0 3px rgba(18, 140, 126, 0.15);
}

.input-invalid {
  border-color: var(--danger) !important;
}

.field-error {
  font-size: 12px;
  color: var(--danger);
  font-weight: 500;
}

.field-hint {
  font-size: 11.5px;
  color: var(--text-muted);
}

.drawer-footer {
  margin-top: auto;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* =================================================================
   MODALS (WHATSAPP & DELETE)
   ================================================================= */
.reminder-modal {
  max-width: 520px;
}

.reminder-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reminder-header-title h3 {
  margin: 0;
  font-size: 18px;
}

.modal-icon-wa {
  font-size: 22px;
}

.client-reminder-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 16px;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.reminder-phone {
  font-family: monospace;
  color: var(--primary);
  font-weight: 600;
}

.reminder-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--border);
  font-size: 12px;
}

.result-detail {
  margin-top: 4px;
  font-size: 12px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.delete-confirm-modal {
  max-width: 440px;
}

.delete-header-title {
  color: var(--danger);
  margin: 0;
}

.delete-warning-text {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 8px;
}

/* =================================================================
   TOAST NOTIFICATION
   ================================================================= */
.floating-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 300;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}

.toast-success {
  background: #054d44;
  color: #fff;
  border: 1px solid #128c7e;
}

.toast-error {
  background: #7f1d1d;
  color: #fff;
  border: 1px solid #ef4444;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.25s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(15px);
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

/* =================================================================
   DARK MODE ADAPTATION
   ================================================================= */
[data-theme="dark"] .matters-table th {
  background: #111827;
  color: var(--text-muted);
}

[data-theme="dark"] .matters-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.03);
}

[data-theme="dark"] .row-overdue {
  background: rgba(220, 38, 38, 0.08) !important;
}

[data-theme="dark"] .row-overdue:hover {
  background: rgba(220, 38, 38, 0.14) !important;
}

[data-theme="dark"] .overdue-badge {
  background: rgba(220, 38, 38, 0.25);
  color: #fca5a5;
}

[data-theme="dark"] .due-today-badge {
  background: rgba(217, 119, 6, 0.25);
  color: #fde047;
}

[data-theme="dark"] .badge-pending {
  background: rgba(217, 119, 6, 0.2);
  color: #fde047;
}

[data-theme="dark"] .badge-in-progress {
  background: rgba(3, 105, 161, 0.25);
  color: #7dd3fc;
}

[data-theme="dark"] .badge-waiting-docs {
  background: rgba(194, 65, 12, 0.25);
  color: #fdba74;
}

[data-theme="dark"] .badge-on-hold {
  background: rgba(126, 34, 206, 0.25);
  color: #d8b4fe;
}

[data-theme="dark"] .badge-under-review {
  background: rgba(67, 56, 202, 0.25);
  color: #a5b4fc;
}

[data-theme="dark"] .badge-completed {
  background: rgba(21, 128, 61, 0.25);
  color: #86efac;
}

[data-theme="dark"] .staff-badge {
  background: #334155;
}

[data-theme="dark"] .followup-badge {
  background: #334155;
}

[data-theme="dark"] .matter-doc-pill {
  background: rgba(3, 105, 161, 0.25);
  color: #7dd3fc;
}

[data-theme="dark"] .btn-action {
  background: #1e293b;
  border-color: #334155;
  color: #f8fafc;
}

[data-theme="dark"] .btn-action-wa {
  background: rgba(37, 211, 102, 0.15);
  border-color: rgba(37, 211, 102, 0.3);
}

[data-theme="dark"] .metric-pill {
  background: #1e293b;
}

[data-theme="dark"] .metric-pill.active {
  background: rgba(18, 140, 126, 0.2);
}

/* =================================================================
   RESPONSIVE DESIGN
   ================================================================= */
@media (max-width: 900px) {
  .header-main {
    flex-direction: column;
  }
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
  .form-row,
  .form-row-3 {
    grid-template-columns: 1fr;
  }
  .drawer-container {
    max-width: 100%;
  }
}
</style>
