<script setup>
import { ref, onMounted, reactive, computed, onBeforeUnmount } from 'vue'
import api from '../services/api'

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
        <p>Manage client profiles and assign them to tax compliance categories.</p>
      </div>
      <button class="btn btn-primary" @click="openAddModal">+ Add Client</button>
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
            <tr v-for="client in clients" :key="client.id">
              <td><strong>{{ client.business_name }}</strong></td>
              <td>{{ client.contact_name }}</td>
              <td>{{ client.mobile_number }}</td>
              
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
</style>
