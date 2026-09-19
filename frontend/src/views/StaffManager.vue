<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'

const router = useRouter()

// ---------------------------------------------------------------
// STATE MANAGEMENT
// ---------------------------------------------------------------
const staffList = ref([])
const metrics = ref({
  total_staff: 0,
  active_staff: 0,
  inactive_staff: 0,
  total_assigned_tasks: 0,
})
const loading = ref(true)
const toast = reactive({ show: false, message: '', type: 'success' })

// Search & Filter State
const searchQuery = ref('')
const roleFilter = ref('ALL')
const statusFilter = ref('ALL') // 'ALL', 'ACTIVE', 'INACTIVE'
const viewMode = ref('table') // 'table' | 'grid'
const sortBy = ref('name') // 'name', 'tasks', 'id'
const sortOrder = ref('asc') // 'asc', 'desc'

// Add / Edit Modal State
const showModal = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const formErrors = reactive({})

const defaultFormData = () => ({
  id: null,
  name: '',
  role: 'Staff',
  email: '',
  mobile_number: '',
  is_active: true,
})
const formData = reactive(defaultFormData())

// Predefined role suggestions
const roleOptions = [
  'Chartered Accountant',
  'Partner / CA',
  'Senior Accountant',
  'Tax Consultant',
  'GST Practitioner',
  'Audit Assistant',
  'Accountant',
  'Article Trainee',
  'Office Administrator',
]

// Assigned Tasks Modal State
const showTasksModal = ref(false)
const selectedStaffMember = ref(null)
const staffTasks = ref([])
const loadingTasks = ref(false)

// WhatsApp Message Modal State
const showWaModal = ref(false)
const waStaff = ref(null)
const waMessage = ref('')
const sendingWa = ref(false)

// Delete Modal State
const showDeleteModal = ref(false)
const staffToDelete = ref(null)
const deleting = ref(false)

// ---------------------------------------------------------------
// TOAST NOTIFICATIONS
// ---------------------------------------------------------------
function showToast(message, type = 'success') {
  toast.message = message
  toast.type = type
  toast.show = true
  setTimeout(() => {
    toast.show = false
  }, 4000)
}

// ---------------------------------------------------------------
// DATA FETCHING
// ---------------------------------------------------------------
async function fetchMetrics() {
  const { data } = await api.getStaffMetrics()
  if (data) {
    metrics.value = data
  }
}

async function fetchStaff() {
  loading.value = true
  const { data, error } = await api.getStaff()
  loading.value = false
  if (error) {
    showToast(error.message || 'Failed to load staff list', 'danger')
  } else if (data) {
    staffList.value = data
  }
}

async function loadData() {
  await Promise.all([fetchStaff(), fetchMetrics()])
}

onMounted(() => {
  loadData()
})

// ---------------------------------------------------------------
// COMPUTED / FILTERED STAFF
// ---------------------------------------------------------------
const availableRoles = computed(() => {
  const roles = new Set(roleOptions)
  staffList.value.forEach((s) => {
    if (s.role) roles.add(s.role)
  })
  return Array.from(roles).sort()
})

const filteredStaff = computed(() => {
  let list = [...staffList.value]

  // Search
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter((s) => {
      const name = (s.name || '').toLowerCase()
      const email = (s.email || '').toLowerCase()
      const mobile = (s.mobile_number || '').toLowerCase()
      const role = (s.role || '').toLowerCase()
      return name.includes(q) || email.includes(q) || mobile.includes(q) || role.includes(q)
    })
  }

  // Filter Role
  if (roleFilter.value !== 'ALL') {
    list = list.filter((s) => s.role === roleFilter.value)
  }

  // Filter Status
  if (statusFilter.value === 'ACTIVE') {
    list = list.filter((s) => s.is_active)
  } else if (statusFilter.value === 'INACTIVE') {
    list = list.filter((s) => !s.is_active)
  }

  // Sorting
  list.sort((a, b) => {
    let comp = 0
    if (sortBy.value === 'name') {
      comp = (a.name || '').localeCompare(b.name || '')
    } else if (sortBy.value === 'tasks') {
      comp = (a.task_count || 0) - (b.task_count || 0)
    } else if (sortBy.value === 'id') {
      comp = (a.id || 0) - (b.id || 0)
    }
    return sortOrder.value === 'asc' ? comp : -comp
  })

  return list
})

// ---------------------------------------------------------------
// AVATAR & COLOR UTILITIES
// ---------------------------------------------------------------
const avatarGradients = [
  'linear-gradient(135deg, #4f46e5, #7c3aed)',
  'linear-gradient(135deg, #059669, #10b981)',
  'linear-gradient(135deg, #0284c7, #38bdf8)',
  'linear-gradient(135deg, #d97706, #fbbf24)',
  'linear-gradient(135deg, #dc2626, #f87171)',
  'linear-gradient(135deg, #7c2d12, #ea580c)',
  'linear-gradient(135deg, #4338ca, #6366f1)',
  'linear-gradient(135deg, #0f766e, #14b8a6)',
]

function getAvatarBackground(name) {
  if (!name) return avatarGradients[0]
  let sum = 0
  for (let i = 0; i < name.length; i++) {
    sum += name.charCodeAt(i)
  }
  return avatarGradients[sum % avatarGradients.length]
}

function getInitials(name) {
  if (!name) return '?'
  const clean = name.replace(/^(CA|Dr|Mr|Ms|Mrs)\.?\s+/i, '').trim()
  const parts = clean.split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function getRoleBadgeClass(role) {
  if (!role) return 'role-default'
  const r = role.toLowerCase()
  if (r.includes('chartered') || r.includes('ca') || r.includes('partner')) return 'role-ca'
  if (r.includes('senior') || r.includes('lead')) return 'role-senior'
  if (r.includes('consultant') || r.includes('advisor')) return 'role-consultant'
  if (r.includes('audit')) return 'role-audit'
  if (r.includes('article') || r.includes('intern') || r.includes('trainee')) return 'role-trainee'
  return 'role-default'
}

function formatPhoneDisplay(num) {
  if (!num) return '—'
  const cleaned = num.replace(/\D/g, '')
  if (cleaned.length === 10) {
    return `+91 ${cleaned.slice(0, 5)} ${cleaned.slice(5)}`
  }
  if (cleaned.length === 12 && cleaned.startsWith('91')) {
    return `+91 ${cleaned.slice(2, 7)} ${cleaned.slice(7)}`
  }
  return num
}

function getWhatsAppUrl(mobile, message = '') {
  if (!mobile) return '#'
  let digits = mobile.replace(/\D/g, '')
  if (digits.length === 10) digits = '91' + digits
  const textParam = message ? `?text=${encodeURIComponent(message)}` : ''
  return `https://wa.me/${digits}${textParam}`
}

// ---------------------------------------------------------------
// CRUD OPERATIONS
// ---------------------------------------------------------------
function openAddModal() {
  Object.assign(formData, defaultFormData())
  clearErrors()
  isEditing.value = false
  showModal.value = true
}

function openEditModal(staff) {
  formData.id = staff.id
  formData.name = staff.name
  formData.role = staff.role || 'Staff'
  formData.email = staff.email || ''
  formData.mobile_number = staff.mobile_number || ''
  formData.is_active = staff.is_active
  clearErrors()
  isEditing.value = true
  showModal.value = true
}

function clearErrors() {
  Object.keys(formErrors).forEach((key) => delete formErrors[key])
}

function validateForm() {
  clearErrors()
  let valid = true

  if (!formData.name.trim()) {
    formErrors.name = 'Full name is required.'
    valid = false
  }

  if (formData.email.trim()) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(formData.email.trim())) {
      formErrors.email = 'Please enter a valid email address.'
      valid = false
    }
  }

  if (formData.mobile_number.trim()) {
    const digits = formData.mobile_number.replace(/\D/g, '')
    if (digits.length < 10 || digits.length > 13) {
      formErrors.mobile_number = 'Mobile number should contain 10-12 digits.'
      valid = false
    }
  }

  return valid
}

async function saveStaff() {
  if (!validateForm()) return

  saving.value = true
  const payload = {
    name: formData.name.trim(),
    role: formData.role.trim() || 'Staff',
    email: formData.email.trim() || null,
    mobile_number: formData.mobile_number.trim() || null,
    is_active: formData.is_active,
  }

  let res
  if (isEditing.value) {
    res = await api.updateStaff(formData.id, payload)
  } else {
    res = await api.createStaff(payload)
  }

  saving.value = false

  if (res.error) {
    showToast(res.error.message || 'Operation failed', 'danger')
  } else {
    showToast(
      isEditing.value
        ? `Staff member "${res.data.name}" updated successfully.`
        : `Staff member "${res.data.name}" added successfully.`,
      'success',
    )
    showModal.value = false
    loadData()
  }
}

async function toggleStatus(staff) {
  const previousState = staff.is_active
  // Optimistic update
  staff.is_active = !previousState

  const { data, error } = await api.toggleStaffStatus(staff.id)
  if (error) {
    staff.is_active = previousState
    showToast(error.message || 'Failed to update status', 'danger')
  } else {
    staff.is_active = data.is_active
    showToast(
      `Staff member marked as ${data.is_active ? 'Active' : 'Inactive'}.`,
      'success',
    )
    fetchMetrics()
  }
}

// ---------------------------------------------------------------
// ASSIGNED TASKS MODAL
// ---------------------------------------------------------------
async function openTasksModal(staff) {
  selectedStaffMember.value = staff
  showTasksModal.value = true
  loadingTasks.value = true
  staffTasks.value = []

  const { data, error } = await api.getStaffMember(staff.id)
  loadingTasks.value = false
  if (error) {
    showToast(error.message || 'Failed to load assigned tasks', 'danger')
  } else if (data) {
    staffTasks.value = data.tasks || []
  }
}

function navigateToTask(taskId) {
  showTasksModal.value = false
  router.push({ path: '/tasks', query: { taskId } })
}

// ---------------------------------------------------------------
// WHATSAPP QUICK MESSAGE MODAL
// ---------------------------------------------------------------
function openWaModal(staff) {
  waStaff.value = staff
  waMessage.value = `Hello ${staff.name},\n\nThis is Gateway Solutions tax management office. Could you please share an update on your assigned compliance tasks?\n\nThank you!`
  showWaModal.value = true
}

function selectWaTemplate(type) {
  if (!waStaff.value) return
  if (type === 'status_check') {
    waMessage.value = `Hello ${waStaff.value.name},\n\nQuick check regarding your pending matters for today. Please review your task dashboard and update progress.\n\nRegards,\nGateway Solutions`
  } else if (type === 'urgent_deadline') {
    waMessage.value = `URGENT REMINDER - ${waStaff.value.name}:\n\nPlease prioritize the compliance filings due within the next 48 hours. Ensure all client documents are verified.\n\nThank you!`
  } else if (type === 'meeting') {
    waMessage.value = `Hi ${waStaff.value.name},\n\nPlease be available for a brief tax filing alignment call in 15 minutes.\n\nGateway Solutions`
  }
}

function sendWaDirect() {
  if (!waStaff.value?.mobile_number) {
    showToast('No phone number available for this staff member', 'danger')
    return
  }
  const url = getWhatsAppUrl(waStaff.value.mobile_number, waMessage.value)
  window.open(url, '_blank')
  showWaModal.value = false
  showToast(`Opened WhatsApp chat with ${waStaff.value.name}`, 'success')
}

// ---------------------------------------------------------------
// DELETE MODAL
// ---------------------------------------------------------------
function openDeleteModal(staff) {
  staffToDelete.value = staff
  showDeleteModal.value = true
}

async function confirmDelete() {
  if (!staffToDelete.value) return

  deleting.value = true
  const { error } = await api.deleteStaff(staffToDelete.value.id)
  deleting.value = false

  if (error) {
    showToast(error.message || 'Failed to delete staff member', 'danger')
  } else {
    showToast(`Staff member "${staffToDelete.value.name}" removed successfully.`, 'success')
    showDeleteModal.value = false
    staffToDelete.value = null
    loadData()
  }
}
</script>

<template>
  <div class="staff-manager-container">
    <!-- Toast Message -->
    <Transition name="toast-fade">
      <div v-if="toast.show" class="toast" :class="`toast-${toast.type}`">
        <span class="toast-icon">
          {{ toast.type === 'success' ? '✓' : toast.type === 'danger' ? '✕' : 'ℹ' }}
        </span>
        <span>{{ toast.message }}</span>
      </div>
    </Transition>

    <!-- ============================= PAGE HEADER ============================= -->
    <div class="header-section">
      <div>
        <div class="header-tag">
          <span class="pulse-indicator"></span> Team & Operations
        </div>
        <h1 class="page-title">Staff Management</h1>
        <p class="page-sub">
          Control staff members, roles, contact details, active status, and track compliance matter assignments.
        </p>
      </div>

      <div class="header-actions">
        <button class="btn btn-outline" @click="loadData" :disabled="loading" title="Refresh data">
          <span class="refresh-icon" :class="{ spinning: loading }">🔄</span> Refresh
        </button>
        <button class="btn btn-primary btn-add" @click="openAddModal">
          <span class="btn-icon">+</span> Add Staff Member
        </button>
      </div>
    </div>

    <!-- ============================= KPI CARDS ============================= -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon-wrap kpi-blue">👥</div>
        <div>
          <div class="kpi-label">Total Staff</div>
          <div class="kpi-val">{{ metrics.total_staff }}</div>
          <div class="kpi-meta">Registered team members</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon-wrap kpi-green">🟢</div>
        <div>
          <div class="kpi-label">Active Members</div>
          <div class="kpi-val">{{ metrics.active_staff }}</div>
          <div class="kpi-meta">Available for assignments</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon-wrap kpi-amber">⏸️</div>
        <div>
          <div class="kpi-label">Inactive / On Leave</div>
          <div class="kpi-val">{{ metrics.inactive_staff }}</div>
          <div class="kpi-meta">Temporarily paused</div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon-wrap kpi-purple">📋</div>
        <div>
          <div class="kpi-label">Tasks Handled</div>
          <div class="kpi-val">{{ metrics.total_assigned_tasks }}</div>
          <div class="kpi-meta">Active compliance matters</div>
        </div>
      </div>
    </div>

    <!-- ============================= TOOLBAR ============================= -->
    <div class="toolbar card">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name, email, mobile, or role..."
          class="search-input"
        />
        <button
          v-if="searchQuery"
          class="clear-search-btn"
          @click="searchQuery = ''"
          title="Clear search"
        >
          ✕
        </button>
      </div>

      <div class="filters-row">
        <!-- Role Filter -->
        <div class="filter-group">
          <label class="filter-label">Role:</label>
          <select v-model="roleFilter" class="select-input">
            <option value="ALL">All Roles</option>
            <option v-for="r in availableRoles" :key="r" :value="r">
              {{ r }}
            </option>
          </select>
        </div>

        <!-- Status Filter -->
        <div class="filter-group">
          <label class="filter-label">Status:</label>
          <div class="status-tabs">
            <button
              class="status-tab"
              :class="{ active: statusFilter === 'ALL' }"
              @click="statusFilter = 'ALL'"
            >
              All
            </button>
            <button
              class="status-tab"
              :class="{ active: statusFilter === 'ACTIVE' }"
              @click="statusFilter = 'ACTIVE'"
            >
              Active
            </button>
            <button
              class="status-tab"
              :class="{ active: statusFilter === 'INACTIVE' }"
              @click="statusFilter = 'INACTIVE'"
            >
              Inactive
            </button>
          </div>
        </div>

        <!-- Sort -->
        <div class="filter-group">
          <label class="filter-label">Sort By:</label>
          <select v-model="sortBy" class="select-input">
            <option value="name">Name</option>
            <option value="tasks">Assigned Tasks</option>
            <option value="id">Date Added</option>
          </select>
          <button
            class="sort-dir-btn"
            @click="sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'"
            :title="sortOrder === 'asc' ? 'Ascending' : 'Descending'"
          >
            {{ sortOrder === 'asc' ? '↑' : '↓' }}
          </button>
        </div>

        <!-- View Mode Switch -->
        <div class="view-mode-switch">
          <button
            class="view-btn"
            :class="{ active: viewMode === 'table' }"
            @click="viewMode = 'table'"
            title="Table View"
          >
            ☰
          </button>
          <button
            class="view-btn"
            :class="{ active: viewMode === 'grid' }"
            @click="viewMode = 'grid'"
            title="Card Grid View"
          >
            ⊞
          </button>
        </div>
      </div>
    </div>

    <!-- ============================= CONTENT LIST ============================= -->
    <div v-if="loading && !staffList.length" class="loading-state card">
      <div class="spinner"></div>
      <p>Loading staff directory...</p>
    </div>

    <div v-else-if="!filteredStaff.length" class="empty-state card">
      <div class="empty-icon">🧑‍💼</div>
      <h3>No staff members found</h3>
      <p v-if="searchQuery || roleFilter !== 'ALL' || statusFilter !== 'ALL'">
        No staff members match the selected filters. Try adjusting your query or filters.
      </p>
      <p v-else>
        Start by adding your team members to assign tasks and streamline WhatsApp tax workflows.
      </p>
      <button class="btn btn-primary mt-3" @click="openAddModal">
        + Add First Staff Member
      </button>
    </div>

    <!-- TABLE VIEW -->
    <div v-else-if="viewMode === 'table'" class="table-card card">
      <div class="table-responsive">
        <table class="staff-table">
          <thead>
            <tr>
              <th>Staff Member</th>
              <th>Role</th>
              <th>Contact</th>
              <th>Assigned Matters</th>
              <th>Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="staff in filteredStaff" :key="staff.id" :class="{ 'row-inactive': !staff.is_active }">
              <!-- Staff Info -->
              <td>
                <div class="staff-meta-cell">
                  <div
                    class="staff-avatar"
                    :style="{ background: getAvatarBackground(staff.name) }"
                  >
                    {{ getInitials(staff.name) }}
                  </div>
                  <div class="staff-names">
                    <div class="staff-fullname">{{ staff.name }}</div>
                    <div v-if="staff.email" class="staff-email">
                      <a :href="`mailto:${staff.email}`">{{ staff.email }}</a>
                    </div>
                    <div v-else class="text-muted-small">No email specified</div>
                  </div>
                </div>
              </td>

              <!-- Role -->
              <td>
                <span class="role-badge" :class="getRoleBadgeClass(staff.role)">
                  {{ staff.role || 'Staff' }}
                </span>
              </td>

              <!-- Contact -->
              <td>
                <div class="contact-cell">
                  <div v-if="staff.mobile_number" class="mobile-row">
                    <a
                      :href="`tel:${staff.mobile_number}`"
                      class="phone-link"
                      title="Call staff"
                    >
                      📞 {{ formatPhoneDisplay(staff.mobile_number) }}
                    </a>
                    <a
                      :href="getWhatsAppUrl(staff.mobile_number)"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="wa-badge-btn"
                      title="Direct WhatsApp chat"
                    >
                      💬 WhatsApp
                    </a>
                  </div>
                  <span v-else class="text-muted-small">No phone number</span>
                </div>
              </td>

              <!-- Assigned Tasks -->
              <td>
                <button
                  class="tasks-pill-btn"
                  @click="openTasksModal(staff)"
                  :title="`Click to view all tasks assigned to ${staff.name}`"
                >
                  <span class="task-count-num">{{ staff.task_count || 0 }}</span>
                  <span class="task-count-label">matters</span>
                  <span v-if="staff.active_task_count > 0" class="active-dot-tag">
                    {{ staff.active_task_count }} active
                  </span>
                </button>
              </td>

              <!-- Status Toggle -->
              <td>
                <div class="status-cell">
                  <button
                    class="status-toggle-pill"
                    :class="staff.is_active ? 'status-active' : 'status-inactive'"
                    @click="toggleStatus(staff)"
                    :title="staff.is_active ? 'Click to mark as Inactive' : 'Click to mark as Active'"
                  >
                    <span class="status-dot-small"></span>
                    {{ staff.is_active ? 'Active' : 'Inactive' }}
                  </button>
                </div>
              </td>

              <!-- Actions -->
              <td class="text-right">
                <div class="actions-group">
                  <button
                    class="icon-action-btn edit-btn"
                    @click="openEditModal(staff)"
                    title="Edit Details"
                  >
                    ✏️
                  </button>
                  <button
                    class="icon-action-btn view-tasks-btn"
                    @click="openTasksModal(staff)"
                    title="View Assigned Tasks"
                  >
                    📋
                  </button>
                  <button
                    v-if="staff.mobile_number"
                    class="icon-action-btn wa-msg-btn"
                    @click="openWaModal(staff)"
                    title="Send WhatsApp Memo"
                  >
                    💬
                  </button>
                  <button
                    class="icon-action-btn delete-btn"
                    @click="openDeleteModal(staff)"
                    title="Delete Staff Member"
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

    <!-- GRID VIEW -->
    <div v-else class="staff-grid">
      <div
        v-for="staff in filteredStaff"
        :key="staff.id"
        class="staff-card card"
        :class="{ 'card-inactive': !staff.is_active }"
      >
        <div class="card-top-accent" :style="{ background: getAvatarBackground(staff.name) }"></div>

        <div class="card-inner">
          <div class="card-header-row">
            <div
              class="staff-avatar avatar-large"
              :style="{ background: getAvatarBackground(staff.name) }"
            >
              {{ getInitials(staff.name) }}
            </div>
            <div class="status-pill-wrap">
              <button
                class="status-toggle-pill"
                :class="staff.is_active ? 'status-active' : 'status-inactive'"
                @click="toggleStatus(staff)"
              >
                <span class="status-dot-small"></span>
                {{ staff.is_active ? 'Active' : 'Inactive' }}
              </button>
            </div>
          </div>

          <div class="card-body-info">
            <h3 class="card-staff-name">{{ staff.name }}</h3>
            <span class="role-badge" :class="getRoleBadgeClass(staff.role)">
              {{ staff.role || 'Staff' }}
            </span>

            <div class="card-contacts">
              <div v-if="staff.mobile_number" class="contact-item">
                <span class="c-icon">📞</span>
                <a :href="`tel:${staff.mobile_number}`">{{ formatPhoneDisplay(staff.mobile_number) }}</a>
              </div>
              <div v-if="staff.email" class="contact-item">
                <span class="c-icon">✉️</span>
                <a :href="`mailto:${staff.email}`">{{ staff.email }}</a>
              </div>
            </div>

            <!-- Task stats bar -->
            <div class="card-task-stats" @click="openTasksModal(staff)">
              <div class="task-stat-left">
                <span class="t-icon">📋</span>
                <span class="t-text"><strong>{{ staff.task_count || 0 }}</strong> matters assigned</span>
              </div>
              <span v-if="staff.active_task_count > 0" class="active-tasks-badge">
                {{ staff.active_task_count }} active
              </span>
            </div>
          </div>

          <!-- Card Actions Footer -->
          <div class="card-footer-actions">
            <button
              v-if="staff.mobile_number"
              class="btn-card btn-card-wa"
              @click="openWaModal(staff)"
              title="Message on WhatsApp"
            >
              💬 WhatsApp
            </button>
            <button
              class="btn-card btn-card-outline"
              @click="openEditModal(staff)"
              title="Edit Staff"
            >
              ✏️ Edit
            </button>
            <button
              class="btn-card btn-card-delete"
              @click="openDeleteModal(staff)"
              title="Delete Staff"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ============================= ADD / EDIT MODAL ============================= -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">{{ isEditing ? 'Edit Staff Member' : 'Add New Staff Member' }}</h3>
            <p class="modal-sub">
              {{ isEditing ? 'Update team member information and status' : 'Register a new staff member to assign tax matters' }}
            </p>
          </div>
          <button class="modal-close-btn" @click="showModal = false">✕</button>
        </div>

        <form @submit.prevent="saveStaff" class="modal-form">
          <!-- Full Name -->
          <div class="form-group">
            <label class="form-label required">Full Name</label>
            <input
              v-model="formData.name"
              type="text"
              class="form-control"
              :class="{ 'is-invalid': formErrors.name }"
              placeholder="e.g. Rahul Sharma or CA Neha Patel"
              autofocus
            />
            <span v-if="formErrors.name" class="invalid-feedback">{{ formErrors.name }}</span>
          </div>

          <!-- Role -->
          <div class="form-group">
            <label class="form-label required">Role / Designation</label>
            <div class="role-input-wrap">
              <select v-model="formData.role" class="form-control">
                <option v-for="r in roleOptions" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
            <span class="help-text">Select role for workload tracking and permissions.</span>
          </div>

          <!-- Mobile Number -->
          <div class="form-group">
            <label class="form-label">
              Mobile Number (WhatsApp)
              <span class="badge-wa-label">WhatsApp Enabled</span>
            </label>
            <div class="input-with-prefix">
              <span class="input-prefix">🇮🇳 +91</span>
              <input
                v-model="formData.mobile_number"
                type="text"
                class="form-control prefix-input"
                :class="{ 'is-invalid': formErrors.mobile_number }"
                placeholder="9876543210"
              />
            </div>
            <span v-if="formErrors.mobile_number" class="invalid-feedback">{{ formErrors.mobile_number }}</span>
            <span v-else class="help-text">Used for instant task alerts and team WhatsApp coordination.</span>
          </div>

          <!-- Email Address -->
          <div class="form-group">
            <label class="form-label">Email Address</label>
            <input
              v-model="formData.email"
              type="email"
              class="form-control"
              :class="{ 'is-invalid': formErrors.email }"
              placeholder="rahul.sharma@gatewaytax.in"
            />
            <span v-if="formErrors.email" class="invalid-feedback">{{ formErrors.email }}</span>
          </div>

          <!-- Active Status Switch -->
          <div class="form-group">
            <label class="status-switch-row">
              <input
                type="checkbox"
                v-model="formData.is_active"
                class="switch-checkbox"
              />
              <span class="switch-slider"></span>
              <div class="switch-labels">
                <span class="switch-title">Active Member</span>
                <span class="switch-sub">
                  {{ formData.is_active ? 'Available for new task assignments' : 'Paused / On leave' }}
                </span>
              </div>
            </label>
          </div>

          <!-- Modal Footer -->
          <div class="modal-footer">
            <button type="button" class="btn btn-outline" @click="showModal = false" :disabled="saving">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="spinner-small"></span>
              {{ saving ? 'Saving...' : (isEditing ? 'Save Changes' : 'Create Staff Member') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ============================= VIEW ASSIGNED TASKS MODAL ============================= -->
    <div v-if="showTasksModal" class="modal-overlay" @click.self="showTasksModal = false">
      <div class="modal-card modal-large">
        <div class="modal-header">
          <div class="modal-header-staff">
            <div
              v-if="selectedStaffMember"
              class="staff-avatar avatar-medium"
              :style="{ background: getAvatarBackground(selectedStaffMember.name) }"
            >
              {{ getInitials(selectedStaffMember.name) }}
            </div>
            <div>
              <h3 class="modal-title">Assigned Matters: {{ selectedStaffMember?.name }}</h3>
              <p class="modal-sub">
                {{ selectedStaffMember?.role }} • {{ staffTasks.length }} total compliance matters
              </p>
            </div>
          </div>
          <button class="modal-close-btn" @click="showTasksModal = false">✕</button>
        </div>

        <div class="modal-body-scrollable">
          <div v-if="loadingTasks" class="loading-state">
            <div class="spinner"></div>
            <p>Loading assigned tasks...</p>
          </div>

          <div v-else-if="!staffTasks.length" class="empty-state-modal">
            <div class="empty-icon">🎉</div>
            <h4>No tasks assigned to {{ selectedStaffMember?.name }}</h4>
            <p class="text-muted">This staff member currently has no active or completed compliance matters.</p>
            <button
              class="btn btn-outline mt-3"
              @click="router.push('/tasks'); showTasksModal = false"
            >
              Go to Tasks Manager to Assign
            </button>
          </div>

          <div v-else class="assigned-tasks-list">
            <div
              v-for="task in staffTasks"
              :key="task.id"
              class="task-item-card"
              @click="navigateToTask(task.id)"
            >
              <div class="task-item-top">
                <div class="task-matter-title">{{ task.matter }}</div>
                <span class="task-status-badge" :class="`status-${(task.status || '').toLowerCase().replace('_', '-')}`">
                  {{ (task.status || '').replace('_', ' ') }}
                </span>
              </div>

              <div class="task-client-row">
                <span class="client-name">🏢 {{ task.client_business_name }}</span>
                <span v-if="task.client_contact_name !== '—'" class="contact-name">
                  ({{ task.client_contact_name }})
                </span>
                <span class="task-due-tag" v-if="task.due_date">
                  📅 Due: {{ task.due_date }}
                </span>
              </div>

              <div v-if="task.remarks" class="task-remarks">
                <strong>Notes:</strong> {{ task.remarks }}
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-outline" @click="showTasksModal = false">
            Close
          </button>
          <button class="btn btn-primary" @click="router.push('/tasks'); showTasksModal = false">
            Open Matters & Tasks Manager →
          </button>
        </div>
      </div>
    </div>

    <!-- ============================= WHATSAPP QUICK MESSAGE MODAL ============================= -->
    <div v-if="showWaModal" class="modal-overlay" @click.self="showWaModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">Send WhatsApp Message</h3>
            <p class="modal-sub">Direct WhatsApp memo to {{ waStaff?.name }}</p>
          </div>
          <button class="modal-close-btn" @click="showWaModal = false">✕</button>
        </div>

        <div class="wa-modal-body">
          <div class="recipient-info">
            <span class="r-label">To:</span>
            <span class="r-name">{{ waStaff?.name }}</span>
            <span class="r-num">({{ formatPhoneDisplay(waStaff?.mobile_number) }})</span>
          </div>

          <!-- Template buttons -->
          <div class="template-selector">
            <label class="form-label">Quick Templates:</label>
            <div class="template-chips">
              <button
                type="button"
                class="chip-btn"
                @click="selectWaTemplate('status_check')"
              >
                📋 Status Check
              </button>
              <button
                type="button"
                class="chip-btn"
                @click="selectWaTemplate('urgent_deadline')"
              >
                ⏰ Urgent Deadline
              </button>
              <button
                type="button"
                class="chip-btn"
                @click="selectWaTemplate('meeting')"
              >
                📞 Quick Call
              </button>
            </div>
          </div>

          <div class="form-group mt-3">
            <label class="form-label">Message Content</label>
            <textarea
              v-model="waMessage"
              class="form-control text-area"
              rows="5"
              placeholder="Type your WhatsApp message..."
            ></textarea>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-outline" @click="showWaModal = false">
            Cancel
          </button>
          <button type="button" class="btn btn-whatsapp" @click="sendWaDirect">
            <span>💬</span> Open WhatsApp Web / App
          </button>
        </div>
      </div>
    </div>

    <!-- ============================= DELETE CONFIRMATION MODAL ============================= -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-card modal-delete">
        <div class="delete-icon-wrap">⚠️</div>
        <h3 class="delete-title">Remove Staff Member?</h3>
        <p class="delete-msg">
          Are you sure you want to delete <strong>"{{ staffToDelete?.name }}"</strong>?
        </p>
        <div v-if="staffToDelete?.task_count > 0" class="delete-warning-box">
          <span class="warn-icon">ℹ️</span>
          <div>
            <strong>Notice:</strong> This staff member has <strong>{{ staffToDelete?.task_count }} matters</strong> assigned.
            Deleting will safely unlink their assignments without deleting the compliance tasks.
          </div>
        </div>
        <p class="delete-sub">This action cannot be undone.</p>

        <div class="modal-footer-centered">
          <button class="btn btn-outline" @click="showDeleteModal = false" :disabled="deleting">
            Cancel
          </button>
          <button class="btn btn-danger" @click="confirmDelete" :disabled="deleting">
            <span v-if="deleting" class="spinner-small"></span>
            {{ deleting ? 'Deleting...' : 'Yes, Delete Staff Member' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* -----------------------------------------------------------------
   ROOT & LAYOUT
   ----------------------------------------------------------------- */
.staff-manager-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Header */
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
}

.header-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(37, 211, 102, 0.12);
  color: #128c7e;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 4px 10px;
  border-radius: 20px;
  margin-bottom: 8px;
}

[data-theme="dark"] .header-tag {
  background: rgba(37, 211, 102, 0.2);
  color: #25d366;
}

.pulse-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #25d366;
  box-shadow: 0 0 0 2px rgba(37, 211, 102, 0.3);
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 6px 0;
}

.page-sub {
  color: var(--text-muted);
  font-size: 14px;
  max-width: 680px;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-add {
  background: linear-gradient(135deg, #075e54, #128c7e);
  color: #fff;
  box-shadow: 0 4px 12px rgba(7, 94, 84, 0.25);
}

.btn-add:hover {
  background: linear-gradient(135deg, #097568, #159c8d);
}

.refresh-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* -----------------------------------------------------------------
   KPI CARDS
   ----------------------------------------------------------------- */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: var(--shadow);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.06);
}

.kpi-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.kpi-blue { background: rgba(59, 130, 246, 0.12); color: #2563eb; }
.kpi-green { background: rgba(37, 211, 102, 0.12); color: #16a34a; }
.kpi-amber { background: rgba(245, 158, 11, 0.12); color: #d97706; }
.kpi-purple { background: rgba(147, 51, 234, 0.12); color: #9333ea; }

.kpi-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
}

.kpi-val {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin: 2px 0;
}

.kpi-meta {
  font-size: 11px;
  color: var(--text-muted);
}

/* -----------------------------------------------------------------
   TOOLBAR
   ----------------------------------------------------------------- */
.toolbar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px;
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0 12px;
  gap: 8px;
}

.search-icon {
  font-size: 15px;
  opacity: 0.6;
}

.search-input {
  border: none;
  background: transparent;
  width: 100%;
  padding: 10px 0;
  font-size: 14px;
  color: var(--text);
  outline: none;
}

.clear-search-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  padding: 4px;
}

.filters-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
}

.select-input {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--text);
  outline: none;
}

.status-tabs {
  display: inline-flex;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 2px;
}

.status-tab {
  border: none;
  background: transparent;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.status-tab.active {
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  font-weight: 600;
}

.sort-dir-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text);
}

.view-mode-switch {
  display: flex;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.view-btn {
  border: none;
  background: var(--surface);
  color: var(--text-muted);
  padding: 6px 12px;
  cursor: pointer;
  font-size: 14px;
}

.view-btn.active {
  background: var(--primary);
  color: #fff;
}

/* -----------------------------------------------------------------
   TABLE VIEW
   ----------------------------------------------------------------- */
.table-card {
  padding: 0;
  overflow: hidden;
}

.table-responsive {
  overflow-x: auto;
}

.staff-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.staff-table th {
  background: var(--bg);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}

.staff-table td {
  padding: 16px 18px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
  vertical-align: middle;
}

.staff-table tbody tr:hover {
  background: rgba(0, 0, 0, 0.015);
}

[data-theme="dark"] .staff-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.row-inactive {
  opacity: 0.65;
}

.staff-meta-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.staff-avatar {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.15);
}

.avatar-large {
  width: 52px;
  height: 52px;
  font-size: 18px;
  border-radius: 14px;
}

.avatar-medium {
  width: 44px;
  height: 44px;
  font-size: 16px;
}

.staff-fullname {
  font-weight: 600;
  color: var(--text);
  font-size: 14px;
}

.staff-email {
  font-size: 12px;
}

.staff-email a {
  color: var(--text-muted);
  text-decoration: none;
}

.staff-email a:hover {
  color: var(--primary);
  text-decoration: underline;
}

.text-muted-small {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

/* Role Badges */
.role-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.role-ca {
  background: #f3e8ff;
  color: #7e22ce;
  border: 1px solid #d8b4fe;
}
[data-theme="dark"] .role-ca {
  background: rgba(126, 34, 206, 0.2);
  color: #d8b4fe;
  border-color: rgba(216, 180, 254, 0.3);
}

.role-senior {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}
[data-theme="dark"] .role-senior {
  background: rgba(4, 120, 87, 0.2);
  color: #6ee7b7;
  border-color: rgba(167, 243, 208, 0.3);
}

.role-consultant {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}
[data-theme="dark"] .role-consultant {
  background: rgba(29, 78, 216, 0.2);
  color: #93c5fd;
  border-color: rgba(191, 219, 254, 0.3);
}

.role-audit {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}
[data-theme="dark"] .role-audit {
  background: rgba(180, 83, 9, 0.2);
  color: #fcd34d;
  border-color: rgba(253, 230, 138, 0.3);
}

.role-trainee {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
}
[data-theme="dark"] .role-trainee {
  background: rgba(71, 85, 105, 0.25);
  color: #cbd5e1;
  border-color: rgba(203, 213, 225, 0.3);
}

.role-default {
  background: #f8fafc;
  color: #334155;
  border: 1px solid #e2e8f0;
}
[data-theme="dark"] .role-default {
  background: rgba(51, 65, 85, 0.3);
  color: #e2e8f0;
  border-color: rgba(226, 232, 240, 0.2);
}

/* Contact Cell */
.contact-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mobile-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.phone-link {
  color: var(--text);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
}

.phone-link:hover {
  color: var(--primary);
}

.wa-badge-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: #25d366;
  color: #054d44;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 12px;
  text-decoration: none;
  transition: transform 0.15s ease;
}

.wa-badge-btn:hover {
  transform: scale(1.05);
}

/* Tasks Pill Button */
.tasks-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 5px 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tasks-pill-btn:hover {
  background: var(--surface);
  border-color: var(--primary);
  transform: translateY(-1px);
}

.task-count-num {
  font-weight: 700;
  color: var(--text);
  font-size: 13px;
}

.task-count-label {
  color: var(--text-muted);
  font-size: 12px;
}

.active-dot-tag {
  background: #dcfce7;
  color: #15803d;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
}
[data-theme="dark"] .active-dot-tag {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

/* Status Pill Toggle */
.status-toggle-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.status-active {
  background: #dcfce7;
  color: #166534;
}
[data-theme="dark"] .status-active {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.status-inactive {
  background: #f1f5f9;
  color: #64748b;
}
[data-theme="dark"] .status-inactive {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.status-dot-small {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

/* Actions Group */
.actions-group {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.icon-action-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.icon-action-btn:hover {
  background: var(--bg);
  border-color: var(--primary);
  transform: translateY(-1px);
}

.delete-btn:hover {
  background: #fee2e2;
  border-color: #f87171;
  color: #dc2626;
}

.text-right {
  text-align: right;
}

/* -----------------------------------------------------------------
   GRID VIEW
   ----------------------------------------------------------------- */
.staff-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.staff-card {
  padding: 0;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.staff-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.08);
}

.card-top-accent {
  height: 6px;
  width: 100%;
}

.card-inner {
  padding: 20px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}

.card-body-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.card-staff-name {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  color: var(--text);
}

.card-contacts {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 8px 0;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.contact-item a {
  color: var(--text-muted);
  text-decoration: none;
}

.contact-item a:hover {
  color: var(--primary);
  text-decoration: underline;
}

.card-task-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  margin-top: 8px;
  transition: background 0.15s ease;
}

.card-task-stats:hover {
  background: rgba(0, 0, 0, 0.04);
}

.task-stat-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text);
}

.active-tasks-badge {
  background: #dcfce7;
  color: #15803d;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.card-footer-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.btn-card {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  padding: 7px 12px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  transition: all 0.15s ease;
}

.btn-card:hover {
  background: var(--bg);
}

.btn-card-wa {
  background: #25d366;
  color: #054d44;
  border-color: #25d366;
  font-weight: 600;
  flex: 1;
}

.btn-card-wa:hover {
  background: #22c55e;
}

.btn-card-delete:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
}

/* -----------------------------------------------------------------
   MODALS
   ----------------------------------------------------------------- */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.modal-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: 100%;
  max-width: 520px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalPop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-large {
  max-width: 720px;
  max-height: 85vh;
}

.modal-delete {
  max-width: 440px;
  text-align: center;
  padding: 28px 24px;
}

@keyframes modalPop {
  from {
    transform: scale(0.95);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.modal-header-staff {
  display: flex;
  align-items: center;
  gap: 14px;
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: var(--text);
}

.modal-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.modal-close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.modal-close-btn:hover {
  color: var(--text);
  background: var(--bg);
}

.modal-form {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-label.required::after {
  content: ' *';
  color: var(--danger);
}

.badge-wa-label {
  font-size: 10px;
  font-weight: 600;
  background: rgba(37, 211, 102, 0.15);
  color: #16a34a;
  padding: 2px 6px;
  border-radius: 10px;
}

.form-control {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s ease;
}

.form-control:focus {
  border-color: var(--primary);
}

.form-control.is-invalid {
  border-color: var(--danger);
}

.invalid-feedback {
  color: var(--danger);
  font-size: 12px;
}

.help-text {
  color: var(--text-muted);
  font-size: 11px;
}

.input-with-prefix {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.input-prefix {
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.03);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  border-right: 1px solid var(--border);
}

.prefix-input {
  border: none;
  background: transparent;
  flex: 1;
}

.status-switch-row {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 10px 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.switch-checkbox {
  display: none;
}

.switch-slider {
  width: 40px;
  height: 22px;
  background: #cbd5e1;
  border-radius: 20px;
  position: relative;
  transition: background 0.2s ease;
  flex-shrink: 0;
}

.switch-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s ease;
}

.switch-checkbox:checked + .switch-slider {
  background: #25d366;
}

.switch-checkbox:checked + .switch-slider::after {
  transform: translateX(18px);
}

.switch-labels {
  display: flex;
  flex-direction: column;
}

.switch-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.switch-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  background: var(--bg);
}

.modal-footer-centered {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}

/* -----------------------------------------------------------------
   ASSIGNED TASKS MODAL
   ----------------------------------------------------------------- */
.modal-body-scrollable {
  padding: 20px 24px;
  overflow-y: auto;
  max-height: 55vh;
}

.assigned-tasks-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.task-item-card:hover {
  background: var(--surface);
  border-color: var(--primary);
  transform: translateY(-1px);
}

.task-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.task-matter-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text);
}

.task-status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 12px;
  text-transform: capitalize;
}

.status-pending { background: #fef3c7; color: #b45309; }
.status-in-progress { background: #e0f2fe; color: #0369a1; }
.status-waiting-documents { background: #ffedd5; color: #c2410c; }
.status-under-review { background: #ede9fe; color: #6d28d9; }
.status-completed { background: #dcfce7; color: #15803d; }
.status-cancelled { background: #f1f5f9; color: #64748b; }

.task-client-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.task-due-tag {
  margin-left: auto;
  font-size: 12px;
  color: var(--text);
  font-weight: 500;
}

.task-remarks {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--border);
}

.empty-state-modal {
  text-align: center;
  padding: 36px 16px;
}

/* -----------------------------------------------------------------
   WHATSAPP MODAL
   ----------------------------------------------------------------- */
.wa-modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.recipient-info {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
}

.r-label {
  color: var(--text-muted);
  font-weight: 500;
}

.r-name {
  font-weight: 600;
  color: var(--text);
}

.r-num {
  color: var(--text-muted);
}

.template-selector {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.template-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip-btn {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text);
  transition: all 0.15s ease;
}

.chip-btn:hover {
  border-color: #25d366;
  background: rgba(37, 211, 102, 0.08);
}

.text-area {
  resize: vertical;
  min-height: 100px;
}

/* -----------------------------------------------------------------
   DELETE MODAL
   ----------------------------------------------------------------- */
.delete-icon-wrap {
  font-size: 38px;
  margin-bottom: 8px;
}

.delete-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 8px 0;
}

.delete-msg {
  font-size: 14px;
  color: var(--text);
  margin: 0 0 12px 0;
}

.delete-warning-box {
  display: flex;
  gap: 10px;
  text-align: left;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 12px;
  margin-bottom: 12px;
}

[data-theme="dark"] .delete-warning-box {
  background: rgba(185, 28, 28, 0.2);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.delete-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

/* -----------------------------------------------------------------
   STATES (EMPTY / LOADING)
   ----------------------------------------------------------------- */
.loading-state,
.empty-state {
  text-align: center;
  padding: 48px 24px;
}

.empty-icon {
  font-size: 44px;
  margin-bottom: 12px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px auto;
}

.spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.mt-3 {
  margin-top: 16px;
}

/* -----------------------------------------------------------------
   TOAST
   ----------------------------------------------------------------- */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
  z-index: 2000;
}

.toast-success { background: #059669; }
.toast-danger { background: #dc2626; }
.toast-info { background: #2563eb; }

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.25s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  transform: translateY(16px);
  opacity: 0;
}
</style>
