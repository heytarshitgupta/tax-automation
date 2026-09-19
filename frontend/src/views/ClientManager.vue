<script setup>
import { ref, onMounted, reactive, computed, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'

const router = useRouter()

const clients = ref([])
const categories = ref([])
const loading = ref(true)
const errorMsg = ref('')
const successMsg = ref('')

// Search state
const searchQuery = ref('')
let searchDebounceTimer = null

// Tax details per-client visibility state
const visibleTaxIds = ref(new Set())

function toggleTaxVisibility(id) {
  if (visibleTaxIds.value.has(id)) {
    visibleTaxIds.value.delete(id)
  } else {
    visibleTaxIds.value.add(id)
  }
}

function isTaxVisible(id) {
  return visibleTaxIds.value.has(id)
}

function getMask(val) {
  if (!val) return ''
  return '*'.repeat(val.length)
}

// Filter panel state
const showFilterPanel = ref(false)
const filterCategoryIds = ref([])
const filterStatus = ref('all') // 'all', 'active', 'inactive'

const activeFilterCount = computed(() => {
  let count = filterCategoryIds.value.length
  if (filterStatus.value !== 'all') count += 1
  return count
})

function toggleFilterPanel() {
  showFilterPanel.value = !showFilterPanel.value
}

function clearFilters() {
  filterCategoryIds.value = []
  filterStatus.value = 'all'
  loadClients()
}

function applyFilters() {
  loadClients()
}

// Status toggle confirmation modal state
const showConfirmModal = ref(false)
const pendingStatusClient = ref(null)
const statusUpdating = ref(false)

// Add/Edit modal state
const showModal = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const formErrors = ref('')

const emptyForm = () => ({
  id: null,
  business_name: '',
  contact_name: '',
  mobile_number: '',
  gst_details: '',
  pan_details: '',
  tan_details: '',
  category_id: '',
  category_ids: [],
  is_active: true,
})

const form = reactive(emptyForm())

async function loadClients() {
  loading.value = true
  errorMsg.value = ''
  const params = {}
  if (searchQuery.value.trim()) {
    params.search = searchQuery.value.trim()
  }
  if (filterCategoryIds.value.length > 0) {
    params.category_ids = filterCategoryIds.value.join(',')
  }
  if (filterStatus.value === 'active') {
    params.is_active = true
  } else if (filterStatus.value === 'inactive') {
    params.is_active = false
  }

  const { data, error } = await api.getClients(params)
  if (error) {
    errorMsg.value = error.message
  } else {
    clients.value = data
  }
  loading.value = false
}

function onSearchInput() {
  clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    loadClients()
  }, 350)
}

function clearSearch() {
  searchQuery.value = ''
  loadClients()
}

async function loadCategories() {
  const { data, error } = await api.getCategories()
  if (!error) categories.value = data
}

// Status toggle handlers with confirmation
function promptStatusChange(client) {
  pendingStatusClient.value = client
  showConfirmModal.value = true
}

function cancelStatusChange() {
  showConfirmModal.value = false
  pendingStatusClient.value = null
}

async function confirmStatusChange() {
  if (!pendingStatusClient.value || statusUpdating.value) return
  const client = pendingStatusClient.value
  const newStatus = !client.is_active

  statusUpdating.value = true
  const { error } = await api.updateClient(client.id, { is_active: newStatus })

  if (error) {
    errorMsg.value = error.message
  } else {
    client.is_active = newStatus
    successMsg.value = `Client "${client.business_name}" marked as ${newStatus ? 'active' : 'inactive'}.`
    setTimeout(() => (successMsg.value = ''), 3000)
  }

  statusUpdating.value = false
  showConfirmModal.value = false
  pendingStatusClient.value = null
}

function openAddModal() {
  Object.assign(form, emptyForm())
  isEditing.value = false
  formErrors.value = ''
  showModal.value = true
}

function openEditModal(client) {
  const catIds = (client.categories && client.categories.length > 0)
    ? client.categories.map(c => c.id)
    : (client.category_id ? [client.category_id] : [])

  Object.assign(form, {
    id: client.id,
    business_name: client.business_name,
    contact_name: client.contact_name,
    mobile_number: client.mobile_number,
    gst_details: client.gst_details || '',
    pan_details: client.pan_details || '',
    tan_details: client.tan_details || '',
    category_id: client.category_id || '',
    category_ids: catIds,
    is_active: client.is_active,
  })
  isEditing.value = true
  formErrors.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function submitForm() {
  formErrors.value = ''
  if (!form.business_name?.trim() || !form.contact_name?.trim() || !form.mobile_number?.trim()) {
    formErrors.value = 'Business name, contact name and mobile number are required.'
    return
  }

  saving.value = true
  const gstClean = form.gst_details ? form.gst_details.trim().toUpperCase() : null
  const panClean = form.pan_details ? form.pan_details.trim().toUpperCase() : null
  const tanClean = form.tan_details ? form.tan_details.trim().toUpperCase() : null

  const payload = {
    business_name: form.business_name.trim(),
    contact_name: form.contact_name.trim(),
    mobile_number: form.mobile_number.trim(),
    gst_details: gstClean || null,
    pan_details: panClean || null,
    tan_details: tanClean || null,
    category_ids: form.category_ids || [],
    category_id: form.category_ids?.length > 0 ? form.category_ids[0] : (form.category_id ? Number(form.category_id) : null),
    is_active: form.is_active,
  }

  const { error } = isEditing.value
    ? await api.updateClient(form.id, payload)
    : await api.createClient(payload)

  if (error) {
    formErrors.value = error.message
  } else {
    successMsg.value = isEditing.value ? 'Client updated successfully.' : 'Client added successfully.'
    showModal.value = false
    await loadClients()
    setTimeout(() => (successMsg.value = ''), 3000)
  }
  saving.value = false
}

async function removeClient(client) {
  if (!confirm(`Delete client "${client.business_name}"? This cannot be undone.`)) return
  const { error } = await api.deleteClient(client.id)
  if (error) {
    errorMsg.value = error.message
  } else {
    successMsg.value = 'Client deleted.'
    await loadClients()
    setTimeout(() => (successMsg.value = ''), 3000)
  }
}

// =================================================================
// CLIENT SELECTION & BATCH NOTIFICATION STATE
// =================================================================
const selectedClientIds = ref([])

const selectedClients = computed(() => {
  return clients.value.filter(c => selectedClientIds.value.includes(c.id))
})

const isAllSelected = computed(() => {
  if (!clients.value || clients.value.length === 0) return false
  return clients.value.every(c => selectedClientIds.value.includes(c.id))
})

const isIndeterminate = computed(() => {
  return selectedClientIds.value.length > 0 && !isAllSelected.value
})

function isSelected(id) {
  return selectedClientIds.value.includes(id)
}

function toggleSelectClient(id) {
  const idx = selectedClientIds.value.indexOf(id)
  if (idx > -1) {
    selectedClientIds.value.splice(idx, 1)
  } else {
    selectedClientIds.value.push(id)
  }
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    const visibleIds = new Set(clients.value.map(c => c.id))
    selectedClientIds.value = selectedClientIds.value.filter(id => !visibleIds.has(id))
  } else {
    const current = new Set(selectedClientIds.value)
    clients.value.forEach(c => current.add(c.id))
    selectedClientIds.value = Array.from(current)
  }
}

function selectByCategory(catId) {
  if (!catId) {
    selectedClientIds.value = clients.value.filter(c => c.is_active).map(c => c.id)
    return
  }
  const matching = clients.value.filter(c => {
    const hasInCategories = c.categories && c.categories.some(cat => cat.id === catId)
    const hasCategory = c.category_id === catId
    return hasInCategories || hasCategory
  })
  const matchingIds = matching.map(c => c.id)
  const allMatchingSelected = matchingIds.length > 0 && matchingIds.every(id => selectedClientIds.value.includes(id))
  if (allMatchingSelected) {
    selectedClientIds.value = selectedClientIds.value.filter(id => !matchingIds.includes(id))
  } else {
    const combined = new Set([...selectedClientIds.value, ...matchingIds])
    selectedClientIds.value = Array.from(combined)
  }
}

function isCategoryFullySelected(catId) {
  const matching = clients.value.filter(c => {
    const hasInCategories = c.categories && c.categories.some(cat => cat.id === catId)
    const hasCategory = c.category_id === catId
    return hasInCategories || hasCategory
  })
  return matching.length > 0 && matching.every(c => selectedClientIds.value.includes(c.id))
}

function clearSelection() {
  selectedClientIds.value = []
}

function getClientCountForCategory(catId) {
  return clients.value.filter(c => {
    const inCats = c.categories && c.categories.some(cat => cat.id === catId)
    const matchesSingle = c.category_id === catId
    return inCats || matchesSingle
  }).length
}

// =================================================================
// NOTIFICATION COMPOSER MODAL STATE
// =================================================================
const showNotificationModal = ref(false)
const notificationMessage = ref('')
const notificationSending = ref(false)
const notificationError = ref('')
const notificationResults = ref(null)
const notificationModalTab = ref('compose') // 'compose' | 'results'
const inModalCategoryFilter = ref('')

const quickTemplates = [
  {
    title: '📋 GST Filing Reminder',
    text: 'Dear {client_name}, this is an important reminder from Gateway Solutions: Your GST return for {business_name} is due shortly. Please submit your sales & purchase records promptly to avoid statutory penalties.',
  },
  {
    title: '📑 Document Request',
    text: 'Dear {client_name}, please share pending bank statements, purchase invoices, and expense vouchers for {business_name} at the earliest to proceed with your filing.',
  },
  {
    title: '💳 Fee Follow-up',
    text: 'Dear {client_name}, this is a gentle follow-up regarding pending professional fee invoice for {business_name}. Kindly arrange the payment at your earliest convenience.',
  },
  {
    title: '📢 Compliance Advisory',
    text: 'Dear {client_name}, important regulatory update from Gateway Solutions for {business_name}: Please review the latest compliance circular issued by the tax department.',
  },
]

function insertPlaceholder(placeholder) {
  notificationMessage.value = (notificationMessage.value || '') + placeholder
}

function applyTemplate(tpl) {
  notificationMessage.value = tpl.text
}

function openNotificationModal(singleClient = null) {
  notificationError.value = ''
  notificationResults.value = null
  notificationModalTab.value = 'compose'
  
  if (singleClient) {
    selectedClientIds.value = [singleClient.id]
  } else if (selectedClientIds.value.length === 0) {
    selectedClientIds.value = clients.value.filter(c => c.is_active).map(c => c.id)
  }

  if (!notificationMessage.value.trim()) {
    notificationMessage.value = 'Dear {client_name}, this is an official update from Gateway Solutions regarding your tax compliance for {business_name}.'
  }

  showNotificationModal.value = true
}

function closeNotificationModal() {
  showNotificationModal.value = false
  notificationResults.value = null
  notificationError.value = ''
}

function removeRecipient(clientId) {
  selectedClientIds.value = selectedClientIds.value.filter(id => id !== clientId)
}

const previewClient = computed(() => {
  if (selectedClients.value.length > 0) return selectedClients.value[0]
  if (clients.value.length > 0) return clients.value[0]
  return {
    business_name: 'Sharma Traders',
    contact_name: 'Rajesh Sharma',
    mobile_number: '919876543210',
  }
})

const previewMessageText = computed(() => {
  const c = previewClient.value
  const raw = notificationMessage.value || ''
  return raw
    .replace(/{client_name}/g, c.contact_name || 'Client')
    .replace(/{business_name}/g, c.business_name || 'Business')
    .replace(/{mobile_number}/g, c.mobile_number || '91XXXXXXXXXX')
})

function formatWhatsAppNumber(mobile) {
  let clean = String(mobile || '').replace(/\D/g, '')
  if (clean.length === 10) {
    clean = '91' + clean
  }
  return clean
}

function getPersonalizedMessage(client, rawTemplate = '') {
  const raw = rawTemplate || notificationMessage.value || 'Hello {client_name}, this is an update from Gateway Solutions regarding your tax compliance.'
  return raw
    .replace(/{client_name}/g, client?.contact_name || 'Client')
    .replace(/{business_name}/g, client?.business_name || 'Business')
    .replace(/{mobile_number}/g, client?.mobile_number || '')
}

function openWhatsAppDirect(client, messageText = '') {
  if (!client || !client.mobile_number) return
  const number = formatWhatsAppNumber(client.mobile_number)
  const text = messageText || getPersonalizedMessage(client)
  const url = `https://wa.me/${number}?text=${encodeURIComponent(text)}`
  window.open(url, '_blank')
}

function getClientById(clientId) {
  return clients.value.find(c => c.id === clientId)
}

async function sendNotificationSubmit() {
  notificationError.value = ''
  if (!selectedClientIds.value || selectedClientIds.value.length === 0) {
    notificationError.value = 'Please select at least one client to notify.'
    return
  }
  if (!notificationMessage.value.trim()) {
    notificationError.value = 'Please enter a text message to send.'
    return
  }

  notificationSending.value = true
  const payload = {
    client_ids: selectedClientIds.value,
    message_type: 'CUSTOM_MESSAGE',
    custom_message: notificationMessage.value.trim(),
  }

  const { data, error } = await api.sendNotifications(payload)
  if (error) {
    notificationError.value = error.message
  } else {
    notificationResults.value = data
    notificationModalTab.value = 'results'
    successMsg.value = `Dispatched WhatsApp message to ${data.sent_count} client(s).`
    setTimeout(() => (successMsg.value = ''), 4000)
  }
  notificationSending.value = false
}

function goToCommunicationLog() {
  closeNotificationModal()
  router.push('/communication-log')
}

// Click outside handler for filter dropdown
function handleWindowClick(e) {
  const filterWrapper = document.querySelector('.filter-dropdown-wrapper')
  if (filterWrapper && !filterWrapper.contains(e.target)) {
    showFilterPanel.value = false
  }
}

onMounted(() => {
  loadClients()
  loadCategories()
  window.addEventListener('click', handleWindowClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', handleWindowClick)
})
</script>

<template>
  <div>
    <div class="page-header header-row">
      <div>
        <h1>Client Manager</h1>
        <p>Manage client profiles, filter by client type, and dispatch custom WhatsApp text messages.</p>
      </div>
      <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap">
        <button class="btn btn-whatsapp" @click="openNotificationModal()">
          <span style="font-size: 16px">💬</span> Send WhatsApp Notification
        </button>
        <button class="btn btn-primary" @click="openAddModal">+ Add Client</button>
      </div>
    </div>

    <div v-if="errorMsg" class="alert alert-error">{{ errorMsg }}</div>
    <div v-if="successMsg" class="alert alert-success">{{ successMsg }}</div>

    <!-- ============================= TOOLBAR: SEARCH & FILTERS ============================= -->
    <div class="table-toolbar">
      <div class="search-input-container">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by business, contact person, or mobile number..."
          class="search-input"
          @input="onSearchInput"
        />
        <button
          v-if="searchQuery"
          type="button"
          class="search-clear-btn"
          @click="clearSearch"
          title="Clear search"
        >
          ✕
        </button>
      </div>

      <!-- Filters Dropdown Trigger & Panel -->
      <div class="filter-dropdown-wrapper">
        <button
          type="button"
          class="btn filter-trigger-btn"
          :class="activeFilterCount > 0 ? 'filter-active-btn' : 'btn-outline'"
          @click.stop="toggleFilterPanel"
        >
          <span class="filter-btn-icon">⚡</span>
          <span>Filters</span>
          <span v-if="activeFilterCount > 0" class="filter-count-badge">{{ activeFilterCount }}</span>
        </button>

        <div v-if="showFilterPanel" class="filter-panel" @click.stop>
          <div class="filter-panel-header">
            <strong>Filter Clients</strong>
            <button
              v-if="activeFilterCount > 0"
              type="button"
              class="filter-clear-btn"
              @click="clearFilters"
            >
              Clear Filters
            </button>
          </div>

          <!-- Section A: Compliance Categories -->
          <div class="filter-section">
            <div class="filter-section-title">Compliance Categories</div>
            <div class="filter-category-list">
              <label
                v-for="cat in categories"
                :key="cat.id"
                class="filter-checkbox-item"
              >
                <input
                  type="checkbox"
                  :value="cat.id"
                  v-model="filterCategoryIds"
                  @change="applyFilters"
                />
                <span>{{ cat.name }}</span>
              </label>
              <div v-if="categories.length === 0" class="filter-empty-text">No categories</div>
            </div>
          </div>

          <!-- Section B: Status Filter -->
          <div class="filter-section">
            <div class="filter-section-title">Client Status</div>
            <div class="filter-status-group">
              <label class="filter-radio-item" :class="{ 'radio-selected': filterStatus === 'all' }">
                <input
                  type="radio"
                  value="all"
                  v-model="filterStatus"
                  @change="applyFilters"
                />
                <span>All</span>
              </label>
              <label class="filter-radio-item" :class="{ 'radio-selected': filterStatus === 'active' }">
                <input
                  type="radio"
                  value="active"
                  v-model="filterStatus"
                  @change="applyFilters"
                />
                <span>Active</span>
              </label>
              <label class="filter-radio-item" :class="{ 'radio-selected': filterStatus === 'inactive' }">
                <input
                  type="radio"
                  value="inactive"
                  v-model="filterStatus"
                  @change="applyFilters"
                />
                <span>Inactive</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ============================= QUICK SELECT BY CLIENT TYPE ============================= -->
    <div class="quick-category-bar">
      <span class="quick-category-title">⚡ Quick Select by Client Type:</span>
      <button
        type="button"
        class="quick-category-pill"
        :class="{ 'pill-active': isAllSelected }"
        @click="toggleSelectAll"
        title="Toggle select all clients"
      >
        All ({{ clients.length }})
      </button>
      <button
        v-for="cat in categories"
        :key="cat.id"
        type="button"
        class="quick-category-pill"
        :class="{ 'pill-active': isCategoryFullySelected(cat.id) }"
        @click="selectByCategory(cat.id)"
        :title="`Select all ${cat.name} clients`"
      >
        <span>{{ cat.name }}</span>
        <span class="pill-count">{{ getClientCountForCategory(cat.id) }}</span>
      </button>
    </div>

    <!-- ============================= BULK SELECTION ACTION BANNER ============================= -->
    <div v-if="selectedClientIds.length > 0" class="selection-banner">
      <div class="selection-banner-left">
        <span class="selection-badge">{{ selectedClientIds.length }}</span>
        <div class="selection-details">
          <strong>{{ selectedClientIds.length }} client(s) selected</strong>
          <span class="selection-sub">Ready for WhatsApp notification</span>
        </div>
      </div>
      <div class="selection-banner-actions">
        <button class="btn btn-whatsapp" @click="openNotificationModal()">
          💬 Compose & Send Message ({{ selectedClientIds.length }})
        </button>
        <button class="btn btn-outline selection-clear-btn" @click="clearSelection">
          Clear Selection
        </button>
      </div>
    </div>

    <!-- ============================= CLIENT TABLE ============================= -->
    <div class="card table-card" style="padding: 0">
      <div v-if="loading" class="loading-state">Loading clients...</div>
      <div v-else-if="clients.length === 0" class="empty-state">
        <template v-if="searchQuery || activeFilterCount > 0">
          <p>No clients found matching current search or filters.</p>
          <div style="display: flex; gap: 8px; justify-content: center; margin-top: 10px">
            <button v-if="searchQuery" class="btn btn-outline" @click="clearSearch">Clear Search</button>
            <button v-if="activeFilterCount > 0" class="btn btn-outline" @click="clearFilters">Clear Filters</button>
          </div>
        </template>
        <template v-else>
          No clients yet. Click "Add Client" to create your first one.
        </template>
      </div>
      <div v-else class="table-responsive">
        <table>
          <thead>
            <tr>
              <th style="width: 44px; text-align: center">
                <input
                  type="checkbox"
                  class="client-select-checkbox"
                  :checked="isAllSelected"
                  :indeterminate="isIndeterminate"
                  @change="toggleSelectAll"
                  title="Select / deselect all clients"
                />
              </th>
              <th>Business</th>
              <th>Contact</th>
              <th>Mobile</th>
              <th>Tax Details</th>
              <th>Categories</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="client in clients"
              :key="client.id"
              :class="{ 'row-selected': isSelected(client.id) }"
            >
              <td style="width: 44px; text-align: center">
                <input
                  type="checkbox"
                  class="client-select-checkbox"
                  :checked="isSelected(client.id)"
                  @change="toggleSelectClient(client.id)"
                  :aria-label="`Select ${client.business_name}`"
                />
              </td>
              <td><strong>{{ client.business_name }}</strong></td>
              <td>{{ client.contact_name }}</td>
              <td>
                <span class="mobile-number-tag">{{ client.mobile_number }}</span>
              </td>
              
              <!-- TAX DETAILS WITH MASKED VALUES & PER-ROW EYE TOGGLE -->
              <td>
                <div v-if="client.gst_details || client.pan_details || client.tan_details" class="tax-cell-box">
                  <div class="tax-lines-wrapper">
                    <div v-if="client.gst_details" class="tax-data-line">
                      <span class="tax-data-lbl">GSTIN</span>
                      <span class="tax-data-val">
                        {{ isTaxVisible(client.id) ? client.gst_details : getMask(client.gst_details) }}
                      </span>
                    </div>
                    <div v-if="client.pan_details" class="tax-data-line">
                      <span class="tax-data-lbl">PAN</span>
                      <span class="tax-data-val">
                        {{ isTaxVisible(client.id) ? client.pan_details : getMask(client.pan_details) }}
                      </span>
                    </div>
                    <div v-if="client.tan_details" class="tax-data-line">
                      <span class="tax-data-lbl">TAN</span>
                      <span class="tax-data-val">
                        {{ isTaxVisible(client.id) ? client.tan_details : getMask(client.tan_details) }}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    class="tax-eye-btn"
                    :class="{ 'tax-eye-active': isTaxVisible(client.id) }"
                    @click="toggleTaxVisibility(client.id)"
                    :title="isTaxVisible(client.id) ? 'Hide tax details' : 'Show tax details'"
                    :aria-label="isTaxVisible(client.id) ? 'Hide tax details' : 'Show tax details'"
                  >
                    <!-- Eye icon (when masked) -->
                    <svg v-if="!isTaxVisible(client.id)" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                    <!-- Eye-off icon (when unmasked) -->
                    <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>
                  </button>
                </div>
                <span v-else class="tax-none-text">—</span>
              </td>

              <!-- CATEGORIES -->
              <td>
                <template v-if="client.categories && client.categories.length > 0">
                  <span
                    v-for="cat in client.categories"
                    :key="cat.id"
                    class="badge badge-info"
                    style="margin-right: 4px; margin-bottom: 2px; display: inline-block"
                  >
                    {{ cat.name }}
                  </span>
                </template>
                <span v-else-if="client.category" class="badge badge-info">{{ client.category.name }}</span>
                <span v-else class="badge badge-neutral">Unassigned</span>
              </td>

              <!-- STATUS TOGGLE SWITCH -->
              <td>
                <div
                  class="status-switch-wrapper"
                  @click="promptStatusChange(client)"
                  :title="`Click to mark as ${client.is_active ? 'inactive' : 'active'}`"
                >
                  <div class="switch-track" :class="client.is_active ? 'switch-on' : 'switch-off'">
                    <div class="switch-knob"></div>
                  </div>
                  <span class="switch-text" :class="client.is_active ? 'text-active' : 'text-inactive'">
                    {{ client.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </div>
              </td>

              <!-- ACTIONS -->
              <td style="white-space: nowrap; text-align: right">
                <button
                  class="btn btn-whatsapp"
                  style="padding: 6px 9px; margin-right: 6px; display: inline-flex; align-items: center; justify-content: center"
                  @click="openWhatsAppDirect(client, `Hello ${client.contact_name || ''}, this is Gateway Solutions regarding your tax compliance for ${client.business_name}.`)"
                  aria-label="WhatsApp"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" style="display: block">
                    <path d="M20.52 3.48A11.93 11.93 0 0 0 12.06 0C5.46 0 .09 5.37.09 11.97c0 2.11.55 4.16 1.6 5.98L0 24l6.23-1.63a11.93 11.93 0 0 0 5.83 1.51h.01c6.6 0 11.97-5.37 11.97-11.97 0-3.2-1.25-6.21-3.52-8.43zm-8.46 18.4h-.01a9.94 9.94 0 0 1-5.07-1.39l-.36-.22-3.77.99 1.01-3.67-.24-.38a9.94 9.94 0 0 1-1.53-5.24c0-5.49 4.47-9.96 9.98-9.96 2.66 0 5.17 1.04 7.05 2.92a9.92 9.92 0 0 1 2.92 7.05c0 5.5-4.47 9.96-9.98 9.96zm5.47-7.46c-.3-.15-1.78-.88-2.06-.98-.27-.1-.47-.15-.67.15-.2.3-.77.98-.95 1.18-.17.2-.35.22-.65.08-.3-.15-1.27-.47-2.42-1.5-.9-.8-1.5-1.79-1.68-2.09-.17-.3-.02-.46.13-.61.13-.14.3-.35.45-.52.15-.18.2-.3.3-.5.1-.2.05-.38-.03-.53-.07-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.08-.79.38-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.06 2.87 1.21 3.07.15.2 2.09 3.19 5.06 4.47.71.31 1.26.49 1.69.63.71.23 1.36.19 1.87.12.57-.09 1.78-.73 2.03-1.43.25-.7.25-1.31.18-1.43-.07-.13-.27-.2-.57-.35z"/>
                  </svg>
                </button>
                <button
                  class="btn btn-whatsapp-outline"
                  style="padding: 6px 10px; margin-right: 6px"
                  @click="openNotificationModal(client)"
                  title="Compose custom WhatsApp notification"
                >
                  💬 Notify
                </button>
                <button class="btn btn-outline" style="padding: 6px 10px; margin-right: 6px" @click="openEditModal(client)">
                  Edit
                </button>
                <button class="btn btn-danger" style="padding: 6px 10px" @click="removeClient(client)">
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ============================= STATUS CONFIRMATION MODAL ============================= -->
    <div v-if="showConfirmModal" class="modal-overlay" @click.self="cancelStatusChange">
      <div class="modal-box confirm-box">
        <div class="modal-header">
          <h3>Confirm Status Change</h3>
          <button class="modal-close" @click="cancelStatusChange">✕</button>
        </div>

        <div class="confirm-body">
          <p>
            Are you sure you want to mark
            <strong>{{ pendingStatusClient?.business_name }}</strong>
            as
            <span :class="pendingStatusClient?.is_active ? 'badge badge-neutral' : 'badge badge-success'">
              {{ pendingStatusClient?.is_active ? 'inactive' : 'active' }}
            </span>?
          </p>
        </div>

        <div class="modal-footer" style="border: none; padding: 0">
          <button type="button" class="btn btn-outline" :disabled="statusUpdating" @click="cancelStatusChange">
            Cancel
          </button>
          <button
            type="button"
            :class="pendingStatusClient?.is_active ? 'btn btn-danger' : 'btn btn-primary'"
            :disabled="statusUpdating"
            @click="confirmStatusChange"
          >
            {{ statusUpdating ? 'Updating...' : 'Confirm' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ============================= ADD/EDIT MODAL (COMPACT & STICKY FOOTER) ============================= -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-box compact-modal-box">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Client' : 'Add New Client' }}</h3>
          <button class="modal-close" @click="closeModal">✕</button>
        </div>

        <form @submit.prevent="submitForm" class="modal-form-container">
          <div class="modal-scroll-body">
            <div v-if="formErrors" class="alert alert-error" style="margin-bottom: 12px">{{ formErrors }}</div>

            <div class="form-group">
              <label>Business Name *</label>
              <input v-model="form.business_name" type="text" placeholder="e.g. Sharma Traders" />
            </div>

            <div class="form-group">
              <label>Contact Person *</label>
              <input v-model="form.contact_name" type="text" placeholder="e.g. Rajesh Sharma" />
            </div>

            <div class="form-group">
              <label>Mobile Number (with country code, no '+') *</label>
              <input v-model="form.mobile_number" type="text" placeholder="e.g. 919876543210" />
            </div>

            <!-- Tax fields in two-column grid on desktop -->
            <div class="form-row-2col">
              <div class="form-group">
                <label>GSTIN</label>
                <input v-model="form.gst_details" type="text" placeholder="e.g. 27AAAPS1234C1Z5" />
              </div>

              <div class="form-group">
                <label>PAN</label>
                <input v-model="form.pan_details" type="text" placeholder="e.g. AAAPS1234C" />
              </div>
            </div>

            <div class="form-row-2col">
              <div class="form-group">
                <label>TAN</label>
                <input v-model="form.tan_details" type="text" placeholder="e.g. PTLA12345B" />
              </div>

              <div class="form-group" style="display: flex; align-items: flex-end; padding-bottom: 6px">
                <label class="compact-active-label">
                  <input type="checkbox" v-model="form.is_active" class="active-checkbox" />
                  <span>Active Client</span>
                </label>
              </div>
            </div>

            <!-- Compliance Categories in compact 2-col grid -->
            <div class="form-group" style="margin-bottom: 4px">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px">
                <label style="margin-bottom: 0">Compliance Categories</label>
                <span v-if="form.category_ids.length > 0" style="font-size: 11px; color: var(--primary); font-weight: 600">
                  {{ form.category_ids.length }} selected
                </span>
              </div>
              <div class="category-selection-container">
                <label
                  v-for="cat in categories"
                  :key="cat.id"
                  class="category-checkbox-item"
                  :class="{ 'category-item-selected': form.category_ids.includes(cat.id) }"
                >
                  <input
                    type="checkbox"
                    :value="cat.id"
                    v-model="form.category_ids"
                    class="category-checkbox"
                  />
                  <span class="category-name">{{ cat.name }}</span>
                </label>
                <div v-if="categories.length === 0" style="font-size: 12px; color: var(--text-muted); padding: 6px">
                  No categories found.
                </div>
              </div>
            </div>
          </div>

          <!-- Sticky Modal Footer -->
          <div class="modal-footer">
            <button type="button" class="btn btn-outline" @click="closeModal">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? 'Saving...' : isEditing ? 'Update Client' : 'Add Client' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ============================= NOTIFICATION COMPOSER MODAL ============================= -->
    <div v-if="showNotificationModal" class="modal-overlay" @click.self="closeNotificationModal">
      <div class="modal-box notification-modal-box">
        <!-- Header -->
        <div class="modal-header notification-modal-header">
          <div class="notification-modal-title-wrap">
            <div class="whatsapp-logo-icon">💬</div>
            <div>
              <h3>Send WhatsApp Notification</h3>
              <p class="modal-subtitle">
                Dispatch personalized text messages to clients' registered mobile numbers via WhatsApp Cloud API
              </p>
            </div>
          </div>
          <button class="modal-close" @click="closeNotificationModal">✕</button>
        </div>

        <!-- Compose Tab -->
        <div v-if="notificationModalTab === 'compose'" class="notification-modal-content">
          <div v-if="notificationError" class="alert alert-error" style="margin-bottom: 14px">
            {{ notificationError }}
          </div>

          <!-- Section 1: Selected Recipients & Client Type Filter -->
          <div class="modal-section-card recipient-section">
            <div class="recipient-section-top">
              <div class="recipient-count-title">
                <strong>Target Recipients</strong>
                <span class="badge badge-success">{{ selectedClientIds.length }} Selected</span>
              </div>
              <div class="recipient-toggles">
                <button type="button" class="btn-text-link" @click="toggleSelectAll">
                  {{ isAllSelected ? 'Deselect All' : 'Select All Active' }}
                </button>
                <button v-if="selectedClientIds.length > 0" type="button" class="btn-text-link" @click="clearSelection">
                  Clear
                </button>
              </div>
            </div>

            <!-- Client Type Quick Toggles -->
            <div class="modal-type-chips-row">
              <span class="type-chips-label">Filter/Toggle Client Type:</span>
              <button
                v-for="cat in categories"
                :key="cat.id"
                type="button"
                class="category-toggle-chip"
                :class="{ 'chip-active': isCategoryFullySelected(cat.id) }"
                @click="selectByCategory(cat.id)"
                :title="`Toggle clients in ${cat.name}`"
              >
                <span>{{ cat.name }}</span>
                <span class="chip-count">({{ getClientCountForCategory(cat.id) }})</span>
              </button>
            </div>

            <!-- Selected Recipient Chips List -->
            <div v-if="selectedClients.length > 0" class="recipient-chips-wrapper">
              <div
                v-for="c in selectedClients"
                :key="c.id"
                class="recipient-chip"
              >
                <span class="chip-business">{{ c.business_name }}</span>
                <span class="chip-contact">({{ c.contact_name }})</span>
                <span class="chip-phone">📱 {{ c.mobile_number }}</span>
                <button
                  type="button"
                  class="chip-remove-btn"
                  @click="removeRecipient(c.id)"
                  title="Remove from recipients"
                >
                  ✕
                </button>
              </div>
            </div>
            <div v-else class="empty-recipients-warning">
              ⚠️ No clients selected. Please click a client type above or pick clients from the table.
            </div>
          </div>

          <!-- Section 2: Composer Layout (Message Editor + Live Preview) -->
          <div class="composer-split-layout">
            <!-- Left: Message Editor -->
            <div class="composer-editor-pane">
              <!-- Quick Tax Templates -->
              <div class="form-group" style="margin-bottom: 12px">
                <div class="input-label-row">
                  <label>Quick Tax Office Templates</label>
                  <span class="input-hint">Click to load</span>
                </div>
                <div class="template-chips-grid">
                  <button
                    v-for="(tpl, idx) in quickTemplates"
                    :key="idx"
                    type="button"
                    class="template-pill-btn"
                    @click="applyTemplate(tpl)"
                  >
                    {{ tpl.title }}
                  </button>
                </div>
              </div>

              <!-- Message Textarea -->
              <div class="form-group" style="margin-bottom: 8px">
                <div class="input-label-row">
                  <label>Message Content *</label>
                  <span class="char-count-badge">{{ notificationMessage.length }} chars</span>
                </div>
                <textarea
                  v-model="notificationMessage"
                  rows="6"
                  class="notification-textarea"
                  placeholder="Enter the message you want to send on clients' mobile numbers..."
                ></textarea>
              </div>

              <!-- Variable Insert Tags -->
              <div class="variable-tag-bar">
                <span class="var-bar-title">Insert Dynamic Tags:</span>
                <button
                  type="button"
                  class="var-pill-btn"
                  @click="insertPlaceholder('{client_name}')"
                  title="Inserts contact person's name"
                >
                  + {client_name}
                </button>
                <button
                  type="button"
                  class="var-pill-btn"
                  @click="insertPlaceholder('{business_name}')"
                  title="Inserts business name"
                >
                  + {business_name}
                </button>
                <button
                  type="button"
                  class="var-pill-btn"
                  @click="insertPlaceholder('{mobile_number}')"
                  title="Inserts mobile number"
                >
                  + {mobile_number}
                </button>
              </div>

              <div class="whatsapp-hint-alert">
                <span class="hint-icon">💡</span>
                <div class="hint-text">
                  WhatsApp formatting: <strong>*bold*</strong>, <em>_italics_</em>, ~strikethrough~.
                  Placeholders will be personalized individually for each client.
                </div>
              </div>
            </div>

            <!-- Right: Live WhatsApp Phone Preview -->
            <div class="composer-preview-pane">
              <div class="preview-header-bar">
                <span>📱 Live WhatsApp Preview</span>
                <span class="preview-client-lbl">Previewing: <strong>{{ previewClient.contact_name }}</strong></span>
              </div>

              <div class="whatsapp-mock-phone">
                <!-- Phone Top Bar -->
                <div class="mock-top-header">
                  <div class="mock-avatar">GS</div>
                  <div class="mock-header-text">
                    <div class="mock-name">Gateway Solutions</div>
                    <div class="mock-to-details">To: +{{ previewClient.mobile_number }} ({{ previewClient.business_name }})</div>
                  </div>
                </div>

                <!-- Chat Body -->
                <div class="mock-chat-screen">
                  <div class="mock-date-pill">TODAY</div>
                  <div class="mock-chat-bubble">
                    <div class="bubble-content-text">
                      {{ previewMessageText || '(Enter a message to see preview)' }}
                    </div>
                    <div class="bubble-meta">
                      <span class="bubble-time">12:30 PM</span>
                      <span class="bubble-ticks">✓✓</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Quick Direct Send from Preview -->
              <div style="margin-top: 10px; display: flex; justify-content: flex-end">
                <button
                  type="button"
                  class="btn btn-whatsapp-outline"
                  style="font-size: 12.5px; padding: 6px 12px"
                  @click="openWhatsAppDirect(previewClient, previewMessageText)"
                  title="Open this preview message directly in WhatsApp Web / App"
                >
                  📱 Test / Open Preview in WhatsApp
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Results Tab (Post-Send) -->
        <div v-else-if="notificationModalTab === 'results'" class="notification-modal-content">
          <div class="results-banner-box">
            <div class="results-check-circle">✓</div>
            <div>
              <h3>WhatsApp Notifications Dispatched</h3>
              <p>Summary of outgoing messages. If running in Simulation mode, click "Send in WhatsApp" to deliver to real mobile numbers instantly!</p>
            </div>
          </div>

          <!-- Stat Cards -->
          <div class="results-stats-row">
            <div class="result-card stat-targeted">
              <span class="stat-number">{{ notificationResults?.total_targeted || 0 }}</span>
              <span class="stat-label">Total Targeted</span>
            </div>
            <div class="result-card stat-sent">
              <span class="stat-number">{{ notificationResults?.sent_count || 0 }}</span>
              <span class="stat-label">Processed</span>
            </div>
            <div class="result-card stat-failed">
              <span class="stat-number">{{ notificationResults?.failed_count || 0 }}</span>
              <span class="stat-label">Failed</span>
            </div>
          </div>

          <!-- Results Details Table -->
          <div class="results-table-box">
            <table>
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Mobile Number</th>
                  <th>Status</th>
                  <th>Details / Note</th>
                  <th style="text-align: right">Direct Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="res in notificationResults?.results || []" :key="res.client_id">
                  <td>
                    <strong>{{ res.business_name }}</strong>
                    <div style="font-size: 11px; color: var(--text-muted)">{{ res.contact_name }}</div>
                  </td>
                  <td>{{ res.mobile_number }}</td>
                  <td>
                    <span :class="res.status === 'SENT' ? 'badge badge-success' : 'badge badge-danger'">
                      {{ res.status }}
                    </span>
                  </td>
                  <td style="font-size: 12px; color: var(--text-muted)">
                    {{ res.detail || (res.simulated ? 'Delivered in Simulation mode' : 'Dispatched via Meta WhatsApp API') }}
                  </td>
                  <td style="text-align: right; white-space: nowrap">
                    <button
                      type="button"
                      class="btn btn-whatsapp"
                      style="padding: 5px 10px; font-size: 12px"
                      @click="openWhatsAppDirect(getClientById(res.client_id) || res, getPersonalizedMessage(getClientById(res.client_id) || res))"
                      title="Send this message via WhatsApp Web or Mobile app directly to mobile"
                    >
                      📱 Send in WhatsApp
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Footer -->
        <div class="modal-footer notification-modal-footer">
          <template v-if="notificationModalTab === 'compose'">
            <button
              type="button"
              class="btn btn-outline"
              :disabled="notificationSending"
              @click="closeNotificationModal"
            >
              Cancel
            </button>
            <button
              v-if="selectedClientIds.length === 1"
              type="button"
              class="btn btn-whatsapp-outline"
              :disabled="notificationSending || !notificationMessage.trim()"
              @click="openWhatsAppDirect(previewClient, previewMessageText)"
              title="Open WhatsApp Web or App directly with this message"
            >
              📱 Open in WhatsApp (1-Click)
            </button>
            <button
              type="button"
              class="btn btn-whatsapp"
              :disabled="notificationSending || selectedClientIds.length === 0 || !notificationMessage.trim()"
              @click="sendNotificationSubmit"
            >
              <span v-if="notificationSending">🚀 Dispatching WhatsApp Messages...</span>
              <span v-else>💬 Send WhatsApp Notification ({{ selectedClientIds.length }} Clients)</span>
            </button>
          </template>
          <template v-else>
            <button type="button" class="btn btn-outline" @click="goToCommunicationLog">
              📜 View in Communication Log
            </button>
            <button type="button" class="btn btn-primary" @click="closeNotificationModal">
              Done
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

/* =================================================================
   TOOLBAR: SEARCH & FILTERS
   ================================================================= */
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.search-input-container {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 480px;
  min-width: 260px;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 13px;
  opacity: 0.6;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 9px 36px 9px 34px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13.5px;
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-light);
  box-shadow: 0 0 0 3px rgba(18, 140, 126, 0.12);
}

.search-clear-btn {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
}

.search-clear-btn:hover {
  color: var(--text);
  background: rgba(0, 0, 0, 0.05);
}

/* Filter Dropdown */
.filter-dropdown-wrapper {
  position: relative;
}

.filter-trigger-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
}

.filter-btn-icon {
  font-size: 12px;
}

.filter-count-badge {
  background: var(--primary);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 999px;
  line-height: 1.4;
}

.filter-active-btn {
  background: #ecfdf5;
  color: var(--primary);
  border: 1px solid var(--primary);
}

[data-theme="dark"] .filter-active-btn {
  background: rgba(18, 140, 126, 0.2);
  color: var(--accent);
}

.filter-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  width: 280px;
  padding: 14px;
  z-index: 50;
}

.filter-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
  font-size: 13px;
}

.filter-clear-btn {
  background: none;
  border: none;
  font-size: 11.5px;
  color: var(--primary);
  cursor: pointer;
  padding: 0;
  font-weight: 600;
}

.filter-clear-btn:hover {
  text-decoration: underline;
}

.filter-section {
  margin-bottom: 12px;
}

.filter-section:last-child {
  margin-bottom: 0;
}

.filter-section-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.filter-category-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 140px;
  overflow-y: auto;
}

.filter-checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
}

.filter-checkbox-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

[data-theme="dark"] .filter-checkbox-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.filter-status-group {
  display: flex;
  gap: 6px;
}

.filter-radio-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  padding: 5px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-radio-item input {
  display: none;
}

.filter-radio-item.radio-selected {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
  font-weight: 600;
}

/* =================================================================
   TABLE & CELLS
   ================================================================= */
.table-card {
  overflow: hidden;
}

.table-responsive {
  width: 100%;
  overflow-x: auto;
}

/* Tax Details Cell — Fixed Height Masked Layout with Zero Layout Shift */
.tax-cell-box {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 185px;
}

.tax-lines-wrapper {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tax-data-line {
  display: flex;
  align-items: center;
  gap: 6px;
  line-height: 1.35;
  white-space: nowrap;
}

.tax-data-lbl {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  width: 36px;
  flex-shrink: 0;
  letter-spacing: 0.5px;
}

.tax-data-val {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--text);
  letter-spacing: 0.5px;
}

.tax-eye-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.tax-eye-btn:hover {
  color: var(--primary);
  border-color: var(--primary-light);
  background: rgba(18, 140, 126, 0.08);
}

.tax-eye-active {
  color: var(--primary);
  border-color: var(--primary);
  background: rgba(18, 140, 126, 0.12);
}

.tax-none-text {
  color: var(--text-muted);
  font-size: 13px;
}

/* Status Switch */
.status-switch-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  padding: 3px 6px;
  border-radius: 6px;
  transition: background 0.15s ease;
}

.status-switch-wrapper:hover {
  background: rgba(0, 0, 0, 0.04);
}

[data-theme="dark"] .status-switch-wrapper:hover {
  background: rgba(255, 255, 255, 0.05);
}

.switch-track {
  width: 34px;
  height: 18px;
  border-radius: 999px;
  position: relative;
  transition: background-color 0.2s ease;
  flex-shrink: 0;
}

.switch-on {
  background-color: var(--success);
}

.switch-off {
  background-color: #cbd5e1;
}

[data-theme="dark"] .switch-off {
  background-color: #475569;
}

.switch-knob {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background-color: #ffffff;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
}

.switch-on .switch-knob {
  transform: translateX(16px);
}

.switch-text {
  font-size: 12.5px;
  font-weight: 600;
  white-space: nowrap;
}

.text-active {
  color: var(--success);
}

.text-inactive {
  color: var(--text-muted);
}

/* =================================================================
   MODALS: COMPACT & FIXED/STICKY LAYOUT
   ================================================================= */
.compact-modal-box {
  background: var(--surface);
  border-radius: var(--radius);
  width: 100%;
  max-width: 520px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.modal-header h3 {
  margin: 0;
  font-size: 17px;
}

.modal-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--text-muted);
  line-height: 1;
}

.modal-form-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.modal-scroll-body {
  padding: 16px 20px 10px 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-shrink: 0;
}

/* Form inputs compact styling */
.form-group {
  margin-bottom: 11px;
}

.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--text);
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 7px 11px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13.5px;
  background: #fff;
  transition: border-color 0.15s ease;
}

[data-theme="dark"] .form-group input,
[data-theme="dark"] .form-group select {
  background: var(--surface);
  color: var(--text);
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--primary-light);
}

.form-row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.compact-active-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
}

.active-checkbox {
  width: 16px !important;
  height: 16px !important;
  cursor: pointer;
  accent-color: var(--primary);
}

/* Compliance Category Compact Grid */
.category-selection-container {
  border: 1px solid var(--border);
  border-radius: 6px;
  max-height: 115px;
  overflow-y: auto;
  padding: 5px 8px;
  background: #fff;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 8px;
}

[data-theme="dark"] .category-selection-container {
  background: var(--surface);
}

.category-checkbox-item {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 7px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
  font-weight: normal;
  margin-bottom: 0;
  transition: background 0.15s ease;
  user-select: none;
}

.category-checkbox-item:hover {
  background: #f1f5f9;
}

[data-theme="dark"] .category-checkbox-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.category-checkbox-item.category-item-selected {
  background: #ecfdf5;
  color: var(--primary);
  font-weight: 500;
}

[data-theme="dark"] .category-checkbox-item.category-item-selected {
  background: rgba(18, 140, 126, 0.15);
}

.category-checkbox {
  accent-color: var(--primary);
  width: 14px !important;
  height: 14px !important;
  cursor: pointer;
  flex-shrink: 0;
}

.category-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Status Confirmation Dialog */
.confirm-box {
  max-width: 420px;
  padding: 20px;
}

.confirm-body {
  padding: 6px 0 16px 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text);
}

@media (max-width: 600px) {
  .form-row-2col {
    grid-template-columns: 1fr;
    gap: 0;
  }
  .category-selection-container {
    grid-template-columns: 1fr;
  }
}

/* =================================================================
   WHATSAPP & BULK NOTIFICATION COMPONENT STYLES
   ================================================================= */
.btn-whatsapp {
  background: #25d366;
  color: #054d44;
  font-weight: 600;
  border: 1px solid #1ebe5d;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

.btn-whatsapp:hover:not(:disabled) {
  background: #20ba5a;
  color: #033630;
  box-shadow: 0 2px 5px rgba(37, 211, 102, 0.25);
}

.btn-whatsapp-outline {
  background: transparent;
  color: #128c7e;
  border: 1px solid #128c7e;
  font-size: 13px;
  font-weight: 500;
}

.btn-whatsapp-outline:hover:not(:disabled) {
  background: #ecfdf5;
  color: #075e54;
}

[data-theme="dark"] .btn-whatsapp {
  background: #25d366;
  color: #0b141a;
}

[data-theme="dark"] .btn-whatsapp-outline {
  color: #25d366;
  border-color: #25d366;
}

[data-theme="dark"] .btn-whatsapp-outline:hover:not(:disabled) {
  background: rgba(37, 211, 102, 0.15);
}

/* Quick Select by Client Type Bar */
.quick-category-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
  padding: 10px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.quick-category-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-right: 4px;
}

.quick-category-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.quick-category-pill:hover {
  border-color: var(--primary);
  background: var(--surface);
  color: var(--primary);
}

.quick-category-pill.pill-active {
  background: #ecfdf5;
  border-color: #10b981;
  color: #065f46;
  font-weight: 600;
}

[data-theme="dark"] .quick-category-pill.pill-active {
  background: rgba(16, 185, 129, 0.2);
  border-color: #10b981;
  color: #6ee7b7;
}

.pill-count {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.08);
  font-weight: 600;
}

[data-theme="dark"] .pill-count {
  background: rgba(255, 255, 255, 0.15);
}

/* Selection Floating Banner */
.selection-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  margin-bottom: 14px;
  background: linear-gradient(90deg, #ecfdf5 0%, #f0fdf4 100%);
  border: 1.5px solid #10b981;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.12);
  animation: slideDown 0.2s ease-out;
  flex-wrap: wrap;
  gap: 12px;
}

[data-theme="dark"] .selection-banner {
  background: linear-gradient(90deg, #064e3b 0%, #022c22 100%);
  border-color: #059669;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.selection-banner-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selection-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #10b981;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
}

.selection-details {
  display: flex;
  flex-direction: column;
}

.selection-details strong {
  font-size: 14px;
  color: #065f46;
}

[data-theme="dark"] .selection-details strong {
  color: #6ee7b7;
}

.selection-sub {
  font-size: 12px;
  color: var(--text-muted);
}

.selection-banner-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selection-clear-btn {
  background: var(--surface) !important;
  border-color: var(--border) !important;
  color: var(--text-muted) !important;
}

.selection-clear-btn:hover {
  color: var(--danger) !important;
  border-color: var(--danger) !important;
}

/* Checkbox and table row selection */
.client-select-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--primary);
}

tr.row-selected {
  background: #f0fdf4 !important;
}

[data-theme="dark"] tr.row-selected {
  background: rgba(18, 140, 126, 0.15) !important;
}

.mobile-number-tag {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  background: var(--bg);
  padding: 3px 7px;
  border-radius: 5px;
  border: 1px solid var(--border);
  color: var(--text);
  letter-spacing: 0.4px;
}

/* =================================================================
   NOTIFICATION COMPOSER MODAL STYLES
   ================================================================= */
.notification-modal-box {
  max-width: 960px;
  width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  border-radius: 14px;
}

.notification-modal-header {
  padding: 18px 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.notification-modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
}

.whatsapp-logo-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, #25d366, #128c7e);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 2px 8px rgba(37, 211, 102, 0.3);
}

.notification-modal-content {
  padding: 20px 24px;
  overflow-y: auto;
  max-height: calc(90vh - 145px);
  background: var(--bg);
}

.notification-modal-footer {
  padding: 14px 24px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* Recipient Section */
.modal-section-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}

.recipient-section-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.recipient-count-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.recipient-count-title strong {
  font-size: 14px;
}

.btn-text-link {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  padding: 2px 6px;
  text-decoration: underline;
}

.btn-text-link:hover {
  color: var(--primary-light);
}

.modal-type-chips-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.type-chips-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.category-toggle-chip {
  padding: 4px 9px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: var(--bg);
  font-size: 12px;
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s ease;
}

.category-toggle-chip:hover {
  border-color: var(--primary);
}

.category-toggle-chip.chip-active {
  background: #ecfdf5;
  border-color: #10b981;
  color: #065f46;
  font-weight: 600;
}

[data-theme="dark"] .category-toggle-chip.chip-active {
  background: rgba(16, 185, 129, 0.2);
  border-color: #10b981;
  color: #6ee7b7;
}

.chip-count {
  font-size: 10.5px;
  opacity: 0.8;
  margin-left: 2px;
}

.recipient-chips-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 120px;
  overflow-y: auto;
  padding-right: 4px;
}

.recipient-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 12px;
}

.chip-business {
  font-weight: 600;
  color: var(--text);
}

.chip-contact {
  color: var(--text-muted);
}

.chip-phone {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 11px;
  color: var(--primary);
}

.chip-remove-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  padding: 1px 4px;
  border-radius: 4px;
}

.chip-remove-btn:hover {
  background: rgba(220, 38, 38, 0.15);
  color: var(--danger);
}

.empty-recipients-warning {
  padding: 12px;
  border-radius: 6px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  font-size: 13px;
}

[data-theme="dark"] .empty-recipients-warning {
  background: #78350f33;
  border-color: #b45309;
  color: #fde68a;
}

/* Composer Split Layout */
.composer-split-layout {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 18px;
  align-items: start;
}

.composer-editor-pane {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px;
}

.input-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.input-label-row label {
  margin: 0;
  font-weight: 600;
  font-size: 13px;
}

.input-hint {
  font-size: 11.5px;
  color: var(--text-muted);
}

.char-count-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text-muted);
}

.template-chips-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.template-pill-btn {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  color: var(--text);
  transition: all 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-pill-btn:hover {
  background: #ecfdf5;
  border-color: #10b981;
  color: #065f46;
}

[data-theme="dark"] .template-pill-btn:hover {
  background: rgba(16, 185, 129, 0.2);
  color: #6ee7b7;
}

.notification-textarea {
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  padding: 10px 12px;
  font-family: inherit;
  font-size: 13.5px;
  line-height: 1.5;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s ease;
}

.notification-textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(18, 140, 126, 0.15);
}

/* Variable Insertion Bar */
.variable-tag-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.var-bar-title {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
}

.var-pill-btn {
  background: rgba(18, 140, 126, 0.08);
  border: 1px solid rgba(18, 140, 126, 0.3);
  color: var(--primary);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 11.5px;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.var-pill-btn:hover {
  background: var(--primary);
  color: #fff;
}

.whatsapp-hint-alert {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--bg);
  border: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-muted);
}

.hint-icon {
  flex-shrink: 0;
}

/* WhatsApp Phone Mockup Preview */
.composer-preview-pane {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
}

.preview-header-bar {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 12px;
}

.preview-header-bar span {
  font-size: 13px;
  font-weight: 600;
}

.preview-client-lbl {
  font-size: 11.5px;
  color: var(--text-muted);
}

.whatsapp-mock-phone {
  background: #efeae2;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #d1d7db;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

[data-theme="dark"] .whatsapp-mock-phone {
  background: #0b141a;
  border-color: #222e35;
}

.mock-top-header {
  background: #075e54;
  color: #fff;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.mock-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #25d366;
  color: #075e54;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
}

.mock-name {
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.2;
}

.mock-to-details {
  font-size: 10.5px;
  opacity: 0.85;
}

.mock-chat-screen {
  padding: 16px 12px;
  min-height: 220px;
  display: flex;
  flex-direction: column;
}

.mock-date-pill {
  align-self: center;
  background: rgba(255, 255, 255, 0.85);
  color: #54656f;
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  margin-bottom: 14px;
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.06);
}

[data-theme="dark"] .mock-date-pill {
  background: #182229;
  color: #8696a0;
}

.mock-chat-bubble {
  align-self: flex-start;
  background: #ffffff;
  color: #111b21;
  padding: 9px 12px;
  border-radius: 8px 8px 8px 0px;
  max-width: 95%;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
  position: relative;
  word-break: break-word;
}

[data-theme="dark"] .mock-chat-bubble {
  background: #202c33;
  color: #e9edef;
}

.bubble-content-text {
  font-size: 12.5px;
  line-height: 1.45;
  white-space: pre-wrap;
}

.bubble-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 4px;
}

.bubble-time {
  font-size: 10px;
  color: #667781;
}

[data-theme="dark"] .bubble-time {
  color: #8696a0;
}

.bubble-ticks {
  font-size: 11px;
  color: #53bdeb;
  font-weight: bold;
}

/* Results Mode */
.results-banner-box {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #ecfdf5;
  border: 1px solid #10b981;
  padding: 16px;
  border-radius: 10px;
  margin-bottom: 16px;
}

[data-theme="dark"] .results-banner-box {
  background: #064e3b33;
  border-color: #059669;
}

.results-check-circle {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #10b981;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
}

.results-banner-box h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #065f46;
}

[data-theme="dark"] .results-banner-box h3 {
  color: #6ee7b7;
}

.results-banner-box p {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}

.results-stats-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.result-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.stat-number {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
}

.stat-label {
  font-size: 11.5px;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-top: 4px;
}

.stat-sent .stat-number {
  color: #10b981;
}

.stat-failed .stat-number {
  color: var(--danger);
}

.results-table-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  max-height: 250px;
  overflow-y: auto;
}

.results-table-box table {
  width: 100%;
}

@media (max-width: 850px) {
  .composer-split-layout {
    grid-template-columns: 1fr;
  }
}
</style>

