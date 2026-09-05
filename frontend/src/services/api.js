import axios from 'axios'

// ---------------------------------------------------------------
// Base URL for the FastAPI backend.
// Change this if your backend runs on a different host/port,
// or set VITE_API_BASE_URL in a `.env` file for the frontend.
// ---------------------------------------------------------------
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Central error normalizer so every view gets a consistent, readable message
function normalizeError(error) {
  if (error.response) {
    const detail = error.response.data?.detail
    return {
      message: typeof detail === 'string' ? detail : `Request failed (${error.response.status})`,
      status: error.response.status,
    }
  } else if (error.request) {
    return { message: 'No response from server. Is the backend running?', status: null }
  }
  return { message: error.message || 'Unexpected error occurred.', status: null }
}

async function request(config) {
  try {
    const response = await apiClient.request(config)
    return { data: response.data, error: null }
  } catch (err) {
    return { data: null, error: normalizeError(err) }
  }
}

export default {
  // ---------- Dashboard ----------
  getDashboardMetrics: () => request({ method: 'GET', url: '/dashboard' }),

  // ---------- Clients ----------
  getClients: (params = {}) => request({ method: 'GET', url: '/clients', params }),
  getClient: (id) => request({ method: 'GET', url: `/clients/${id}` }),
  createClient: (payload) => request({ method: 'POST', url: '/clients', data: payload }),
  updateClient: (id, payload) => request({ method: 'PUT', url: `/clients/${id}`, data: payload }),
  deleteClient: (id) => request({ method: 'DELETE', url: `/clients/${id}` }),

  // ---------- Categories ----------
  getCategories: () => request({ method: 'GET', url: '/categories' }),
  createCategory: (payload) => request({ method: 'POST', url: '/categories', data: payload }),
  updateCategory: (id, payload) => request({ method: 'PUT', url: `/categories/${id}`, data: payload }),
  deleteCategory: (id) => request({ method: 'DELETE', url: `/categories/${id}` }),

  // ---------- Message History / Communication Log ----------
  getMessageHistory: (params = {}) => request({ method: 'GET', url: '/message-history', params }),

  // ---------- Invoices ----------
  getInvoices: () => request({ method: 'GET', url: '/invoices' }),
  createInvoice: (payload) => request({ method: 'POST', url: '/invoices', data: payload }),
  sendInvoiceNotification: (id) => request({ method: 'POST', url: `/invoices/${id}/send` }),

  // ---------- Manual Triggers ----------
  runSchedulerNow: () => request({ method: 'POST', url: '/scheduler/run-now' }),
  sendDocumentRequest: (clientId, docDescription) =>
    request({
      method: 'POST',
      url: `/clients/${clientId}/send-document-request`,
      params: { doc_description: docDescription },
    }),
}
