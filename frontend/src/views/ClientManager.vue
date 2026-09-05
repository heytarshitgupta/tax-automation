<script setup>
import { ref, onMounted, reactive } from 'vue'
import api from '../services/api'

const clients = ref([])
const categories = ref([])
const loading = ref(true)
const errorMsg = ref('')
const successMsg = ref('')

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
  category_id: '',
  is_active: true,
})

const form = reactive(emptyForm())

async function loadClients() {
  loading.value = true
  errorMsg.value = ''
  const { data, error } = await api.getClients()
  if (error) {
    errorMsg.value = error.message
  } else {
    clients.value = data
  }
  loading.value = false
}

async function loadCategories() {
  const { data, error } = await api.getCategories()
  if (!error) categories.value = data
}

function openAddModal() {
  Object.assign(form, emptyForm())
  isEditing.value = false
  formErrors.value = ''
  showModal.value = true
}

function openEditModal(client) {
  Object.assign(form, {
    id: client.id,
    business_name: client.business_name,
    contact_name: client.contact_name,
    mobile_number: client.mobile_number,
    gst_details: client.gst_details || '',
    pan_details: client.pan_details || '',
    category_id: client.category_id || '',
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
  if (!form.business_name || !form.contact_name || !form.mobile_number) {
    formErrors.value = 'Business name, contact name and mobile number are required.'
    return
  }

  saving.value = true
  const payload = {
    business_name: form.business_name,
    contact_name: form.contact_name,
    mobile_number: form.mobile_number,
    gst_details: form.gst_details || null,
    pan_details: form.pan_details || null,
    category_id: form.category_id ? Number(form.category_id) : null,
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

onMounted(() => {
  loadClients()
  loadCategories()
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

    <div class="card" style="padding: 0">
      <div v-if="loading" class="loading-state">Loading clients...</div>
      <div v-else-if="clients.length === 0" class="empty-state">
        No clients yet. Click "Add Client" to create your first one.
      </div>
      <table v-else>
        <thead>
          <tr>
            <th>Business</th>
            <th>Contact</th>
            <th>Mobile</th>
            <th>GST No.</th>
            <th>Category</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="client in clients" :key="client.id">
            <td>{{ client.business_name }}</td>
            <td>{{ client.contact_name }}</td>
            <td>{{ client.mobile_number }}</td>
            <td>{{ client.gst_details || '—' }}</td>
            <td>
              <span v-if="client.category" class="badge badge-info">{{ client.category.name }}</span>
              <span v-else class="badge badge-neutral">Unassigned</span>
            </td>
            <td>
              <span :class="client.is_active ? 'badge badge-success' : 'badge badge-neutral'">
                {{ client.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td>
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

    <!-- ============================= ADD/EDIT MODAL ============================= -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-box">
        <div class="modal-header">
          <h3>{{ isEditing ? 'Edit Client' : 'Add New Client' }}</h3>
          <button class="modal-close" @click="closeModal">✕</button>
        </div>

        <div v-if="formErrors" class="alert alert-error">{{ formErrors }}</div>

        <form @submit.prevent="submitForm">
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

          <div class="form-group">
            <label>GST Number</label>
            <input v-model="form.gst_details" type="text" placeholder="e.g. 27AAAPS1234C1Z5" />
          </div>

          <div class="form-group">
            <label>PAN Number</label>
            <input v-model="form.pan_details" type="text" placeholder="e.g. AAAPS1234C" />
          </div>

          <div class="form-group">
            <label>Category</label>
            <select v-model="form.category_id">
              <option value="">-- Unassigned --</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
            </select>
          </div>

          <div class="form-group">
            <label style="display: flex; align-items: center; gap: 8px">
              <input type="checkbox" v-model="form.is_active" style="width: auto" />
              Active Client
            </label>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px">
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
</style>
